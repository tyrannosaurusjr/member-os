from functools import wraps
import csv
import io
import json
from uuid import UUID

from django.contrib import messages
from django.db.models import Count, Prefetch, Q
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import LoginView, LogoutView, PasswordChangeDoneView, PasswordChangeView
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.decorators.http import require_GET
from django.views.decorators.http import require_POST
from django.views import View
from django.views.generic import DetailView, ListView, RedirectView, TemplateView

from .forms import CsvImportForm, StaffAuthenticationForm, StyledPasswordChangeForm
from .imports import CsvImportError, import_external_profiles_from_csv, serialize_import_run
from .models import (
    ExternalProfile,
    ExternalProfileSnapshot,
    MergeCandidate,
    MergeCandidateStatus,
    Person,
    SourceSystem,
    SyncDirection,
    SyncRun,
)

SAMPLE_IMPORT_TEMPLATE_HEADERS = [
    'source_record_id',
    'full_name',
    'primary_email',
    'primary_phone',
    'company',
    'job_title',
    'notes',
]

SAMPLE_IMPORT_TEMPLATE_ROWS = [
    {
        'source_record_id': 'delphi-001',
        'full_name': 'Jane Smith',
        'primary_email': 'jane.smith@example.com',
        'primary_phone': '+14155550100',
        'company': 'Goldman Sachs Japan',
        'job_title': 'Managing Director',
        'notes': 'Registered by assistant for March salon.',
    },
    {
        'source_record_id': 'event-204',
        'full_name': 'David Chen',
        'primary_email': 'david.chen@acme.vc',
        'primary_phone': '+819012345678',
        'company': 'Acme Ventures',
        'job_title': 'Partner',
        'notes': 'Attended before membership application.',
    },
]


def staff_api_required(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'authentication required'}, status=401)
        if not request.user.is_staff:
            return JsonResponse({'error': 'staff access required'}, status=403)
        return view_func(request, *args, **kwargs)

    return _wrapped


class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    login_url = reverse_lazy('login')

    def test_func(self):
        return self.request.user.is_staff

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        raise PermissionDenied('Staff access required.')


class StaffLoginView(LoginView):
    authentication_form = StaffAuthenticationForm
    template_name = 'registration/login.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        return self.get_redirect_url() or reverse_lazy('operator-home')


class StaffLogoutView(LogoutView):
    next_page = reverse_lazy('login')


class OperatorRootView(RedirectView):
    pattern_name = 'operator-home'

    def get_redirect_url(self, *args, **kwargs):
        if not self.request.user.is_authenticated:
            return reverse_lazy('login')
        return super().get_redirect_url(*args, **kwargs)


class OperatorHomeView(StaffRequiredMixin, TemplateView):
    template_name = 'core/operator_home.html'

    def get_recent_import_runs(self):
        return list(
            SyncRun.objects.filter(direction=SyncDirection.INBOUND).order_by('-started_at')[:8]
        )

    def get_selected_import_run(self, recent_import_runs):
        sync_run_id = self.request.GET.get('run')
        if sync_run_id:
            try:
                UUID(sync_run_id)
            except ValueError:
                return None
            return (
                SyncRun.objects.filter(
                    sync_run_id=sync_run_id,
                    direction=SyncDirection.INBOUND,
                )
                .order_by('-started_at')
                .first()
            )
        return recent_import_runs[0] if recent_import_runs else None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        recent_import_runs = kwargs.get('recent_import_runs') or self.get_recent_import_runs()
        selected_import_run = kwargs.get('selected_import_run')
        if selected_import_run is None:
            selected_import_run = self.get_selected_import_run(recent_import_runs)

        context.update(
            {
                'import_form': kwargs.get('import_form') or CsvImportForm(),
                'people_count': Person.objects.count(),
                'external_profiles_count': ExternalProfile.objects.count(),
                'inbound_sync_runs_count': SyncRun.objects.filter(
                    direction=SyncDirection.INBOUND
                ).count(),
                'open_merge_candidates_count': MergeCandidate.objects.filter(
                    status=MergeCandidateStatus.OPEN
                ).count(),
                'unlinked_external_profiles_count': ExternalProfile.objects.filter(
                    person__isnull=True
                ).count(),
                'recent_import_runs': recent_import_runs,
                'selected_import_run': (
                    serialize_import_run(selected_import_run)
                    if selected_import_run
                    else None
                ),
                'selected_import_run_id': (
                    str(selected_import_run.sync_run_id) if selected_import_run else None
                ),
            }
        )
        return context

    def post(self, request, *args, **kwargs):
        import_form = CsvImportForm(request.POST, request.FILES)
        recent_import_runs = self.get_recent_import_runs()

        if import_form.is_valid():
            try:
                result = import_external_profiles_from_csv(
                    import_form.cleaned_data['file'],
                    import_form.cleaned_data['source_system'],
                )
            except CsvImportError as exc:
                import_form.add_error(None, str(exc))
            else:
                summary = (
                    f'Import complete: {result.sync_run.records_processed} processed, '
                    f'{result.sync_run.records_failed} failed.'
                )
                if result.sync_run.records_failed:
                    messages.warning(request, summary)
                else:
                    messages.success(request, summary)
                return redirect(
                    f'{reverse_lazy("operator-home")}?run={result.sync_run.sync_run_id}'
                )

        return self.render_to_response(
            self.get_context_data(
                import_form=import_form,
                recent_import_runs=recent_import_runs,
                selected_import_run=self.get_selected_import_run(recent_import_runs),
            )
        )


class SampleImportTemplateView(StaffRequiredMixin, View):
    def get(self, _request, *args, **kwargs):
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=SAMPLE_IMPORT_TEMPLATE_HEADERS)
        writer.writeheader()
        writer.writerows(SAMPLE_IMPORT_TEMPLATE_ROWS)
        response = HttpResponse(output.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = (
            'attachment; filename="member-os-sample-import.csv"'
        )
        return response


class PeopleDirectoryView(StaffRequiredMixin, ListView):
    template_name = 'core/people_directory.html'
    context_object_name = 'people'
    paginate_by = 50

    def get_queryset(self):
        queryset = (
            Person.objects.annotate(
                external_profile_count=Count('external_profiles', distinct=True)
            )
            .order_by('full_name')
        )
        query = (self.request.GET.get('q') or '').strip()
        if query:
            queryset = queryset.filter(
                Q(full_name__icontains=query)
                | Q(primary_email__icontains=query)
                | Q(company__icontains=query)
                | Q(job_title__icontains=query)
                | Q(external_profiles__source_record_id__icontains=query)
            ).distinct()
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query = (self.request.GET.get('q') or '').strip()
        context.update(
            {
                'query': query,
                'people_count': Person.objects.count(),
                'linked_external_profiles_count': ExternalProfile.objects.filter(
                    person__isnull=False
                ).count(),
                'unlinked_external_profiles_count': ExternalProfile.objects.filter(
                    person__isnull=True
                ).count(),
                'recent_unlinked_profiles': ExternalProfile.objects.filter(
                    person__isnull=True
                ).order_by('-updated_at')[:8],
            }
        )
        return context


class PersonDetailView(StaffRequiredMixin, DetailView):
    template_name = 'core/person_detail.html'
    context_object_name = 'person'
    slug_field = 'person_id'
    slug_url_kwarg = 'person_id'

    def get_queryset(self):
        return Person.objects.prefetch_related(
            Prefetch(
                'external_profiles',
                queryset=ExternalProfile.objects.prefetch_related(
                    'aliases',
                    'snapshots',
                ).order_by('-source_last_seen_at', '-updated_at'),
            ),
            'organization_links__organization',
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        person = context['person']
        recent_snapshots = []
        for snapshot in (
            ExternalProfileSnapshot.objects.filter(external_profile__person=person)
            .select_related('external_profile', 'sync_run')
            .order_by('-created_at')[:12]
        ):
            recent_snapshots.append(
                {
                    'created_at': snapshot.created_at,
                    'observed_at': snapshot.observed_at,
                    'source_system': snapshot.external_profile.get_source_system_display(),
                    'source_record_id': snapshot.external_profile.source_record_id,
                    'sync_run_id': (
                        str(snapshot.sync_run.sync_run_id) if snapshot.sync_run else None
                    ),
                    'raw_payload_pretty': json.dumps(
                        snapshot.raw_payload_json,
                        indent=2,
                        sort_keys=True,
                    ),
                    'normalized_payload_pretty': json.dumps(
                        snapshot.normalized_payload_json,
                        indent=2,
                        sort_keys=True,
                    ),
                }
            )

        context.update(
            {
                'recent_snapshots': recent_snapshots,
                'external_profile_count': person.external_profiles.count(),
            }
        )
        return context


class StaffPasswordChangeView(StaffRequiredMixin, PasswordChangeView):
    form_class = StyledPasswordChangeForm
    template_name = 'registration/password_change_form.html'
    success_url = reverse_lazy('password_change_done')


class StaffPasswordChangeDoneView(StaffRequiredMixin, PasswordChangeDoneView):
    template_name = 'registration/password_change_done.html'


@require_GET
def health(_request):
    return JsonResponse({'status': 'ok'})


@require_POST
@staff_api_required
def import_external_profiles_csv(request):
    uploaded_file = request.FILES.get('file')
    if uploaded_file is None:
        return JsonResponse({'error': 'file is required'}, status=400)

    source_system = request.POST.get('source_system', SourceSystem.MANUAL_CSV)

    try:
        result = import_external_profiles_from_csv(uploaded_file, source_system)
    except CsvImportError as exc:
        return JsonResponse({'error': str(exc)}, status=400)

    return JsonResponse(
        {
            'import_run_id': str(result.sync_run.sync_run_id),
            'records_received': result.records_received,
            'records_processed': result.sync_run.records_processed,
            'records_failed': result.sync_run.records_failed,
        },
        status=201,
    )


@require_GET
@staff_api_required
def import_run_detail(_request, sync_run_id):
    sync_run = get_object_or_404(
        SyncRun,
        sync_run_id=sync_run_id,
        direction=SyncDirection.INBOUND,
    )
    return JsonResponse(serialize_import_run(sync_run))

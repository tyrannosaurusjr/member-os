from functools import wraps

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import LoginView, LogoutView, PasswordChangeDoneView, PasswordChangeView
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.views.decorators.http import require_GET
from django.views.decorators.http import require_POST
from django.views.generic import RedirectView, TemplateView

from .forms import StaffAuthenticationForm, StyledPasswordChangeForm
from .imports import CsvImportError, import_external_profiles_from_csv, serialize_import_run
from .models import (
    ExternalProfile,
    MergeCandidate,
    MergeCandidateStatus,
    Person,
    SourceSystem,
    SyncDirection,
    SyncRun,
)


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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                'people_count': Person.objects.count(),
                'external_profiles_count': ExternalProfile.objects.count(),
                'inbound_sync_runs_count': SyncRun.objects.filter(
                    direction=SyncDirection.INBOUND
                ).count(),
                'open_merge_candidates_count': MergeCandidate.objects.filter(
                    status=MergeCandidateStatus.OPEN
                ).count(),
                'recent_import_runs': SyncRun.objects.filter(
                    direction=SyncDirection.INBOUND
                ).order_by('-started_at')[:5],
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

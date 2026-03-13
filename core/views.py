from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET
from django.views.decorators.http import require_POST

from .imports import CsvImportError, import_external_profiles_from_csv, serialize_import_run
from .models import SourceSystem, SyncDirection, SyncRun

@require_GET
def health(_request):
    return JsonResponse({'status': 'ok'})


@require_POST
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
def import_run_detail(_request, sync_run_id):
    sync_run = get_object_or_404(
        SyncRun,
        sync_run_id=sync_run_id,
        direction=SyncDirection.INBOUND,
    )
    return JsonResponse(serialize_import_run(sync_run))

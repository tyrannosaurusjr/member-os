from django.urls import path

from .views import health, import_external_profiles_csv, import_run_detail


urlpatterns = [
    path('health', health, name='health'),
    path(
        'external-profiles/import/csv',
        import_external_profiles_csv,
        name='external-profiles-import-csv',
    ),
    path(
        'import-runs/<uuid:sync_run_id>',
        import_run_detail,
        name='import-run-detail',
    ),
]

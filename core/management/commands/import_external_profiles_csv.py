from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from core.imports import CsvImportError, import_external_profiles_from_csv
from core.models import SourceSystem


class Command(BaseCommand):
    help = 'Import a CSV file into ExternalProfile records using the standard ingestion pipeline.'

    def add_arguments(self, parser):
        parser.add_argument('csv_path', help='Path to the CSV file to import')
        parser.add_argument(
            '--source-system',
            default=SourceSystem.MANUAL_CSV,
            choices=SourceSystem.values,
            help='Source system label to apply to the import',
        )

    def handle(self, *args, **options):
        csv_path = Path(options['csv_path']).expanduser().resolve()
        source_system = options['source_system']

        if not csv_path.exists():
            raise CommandError(f'CSV file does not exist: {csv_path}')
        if not csv_path.is_file():
            raise CommandError(f'CSV path is not a file: {csv_path}')

        try:
            with csv_path.open('rb') as handle:
                result = import_external_profiles_from_csv(handle, source_system)
        except CsvImportError as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(
            self.style.SUCCESS(
                '\n'.join(
                    [
                        f'import_run_id={result.sync_run.sync_run_id}',
                        f'source_system={source_system}',
                        f'records_received={result.records_received}',
                        f'records_processed={result.sync_run.records_processed}',
                        f'records_failed={result.sync_run.records_failed}',
                    ]
                )
            )
        )

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from .normalization import normalize_email, normalize_name, normalize_phone
from .models import (
    CanonicalMembershipTier,
    ExternalProfile,
    ExternalProfileAlias,
    FieldSourcePriority,
    MergeCandidate,
    Person,
    SourceSystem,
    SyncRun,
)


class HealthEndpointTests(SimpleTestCase):
    def test_health_endpoint_returns_ok(self):
        response = self.client.get(reverse('health'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'status': 'ok'})


class NormalizationTests(SimpleTestCase):
    def test_normalize_email_trims_lowercases_and_removes_spaces(self):
        self.assertEqual(
            normalize_email('  Jane.Smith @Example.COM  '),
            'jane.smith@example.com',
        )

    def test_normalize_email_returns_none_for_blank_values(self):
        self.assertIsNone(normalize_email('   '))
        self.assertIsNone(normalize_email(None))

    def test_normalize_name_collapses_whitespace(self):
        self.assertEqual(
            normalize_name('  Jane   A.   Smith  '),
            'Jane A. Smith',
        )

    def test_normalize_name_returns_none_for_blank_values(self):
        self.assertIsNone(normalize_name(''))
        self.assertIsNone(normalize_name('   '))

    def test_normalize_phone_formats_us_numbers_to_e164_like_output(self):
        self.assertEqual(
            normalize_phone(' (415) 555-0100 '),
            '+14155550100',
        )

    def test_normalize_phone_preserves_existing_international_prefix(self):
        self.assertEqual(
            normalize_phone('+81 90-1234-5678'),
            '+819012345678',
        )

    def test_normalize_phone_converts_double_zero_prefix(self):
        self.assertEqual(
            normalize_phone('0044 20 7946 0958'),
            '+442079460958',
        )

    def test_normalize_phone_strips_extensions(self):
        self.assertEqual(
            normalize_phone('415-555-0100 ext 42'),
            '+14155550100',
        )


class SeedDataTests(TestCase):
    def test_canonical_membership_tier_seed_data_exists(self):
        tier_names = set(
            CanonicalMembershipTier.objects.values_list(
                'canonical_tier_name',
                flat=True,
            )
        )

        self.assertTrue(
            {
                'Core Member',
                'Corporate Member',
                'Complimentary',
                'Prospect',
                'Partner',
            }.issubset(tier_names)
        )

    def test_field_source_priorities_include_whatsapp_and_clay_rules(self):
        priorities = {
            (field_name, source_system): priority_rank
            for field_name, source_system, priority_rank in FieldSourcePriority.objects.values_list(
                'field_name',
                'source_system',
                'priority_rank',
            )
        }

        self.assertEqual(priorities[('phone', SourceSystem.WHATSAPP)], 1)
        self.assertEqual(priorities[('email', SourceSystem.CLAY)], 6)
        self.assertGreater(
            priorities[('name', SourceSystem.WHATSAPP)],
            priorities[('name', SourceSystem.APPLE_CONTACTS)],
        )


class CoreModelConstraintTests(TestCase):
    def test_external_profile_rejects_unknown_source_system(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ExternalProfile.objects.create(
                    source_system='telegram',
                    source_record_id='abc123',
                )

    def test_field_source_priority_uniqueness_is_enforced(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                FieldSourcePriority.objects.create(
                    field_name='email',
                    source_system=SourceSystem.STRIPE,
                    priority_rank=99,
                )

    def test_whatsapp_profiles_can_store_alias_history(self):
        profile = ExternalProfile.objects.create(
            source_system=SourceSystem.WHATSAPP,
            source_record_id='+819012345678',
        )

        ExternalProfileAlias.objects.create(
            external_profile=profile,
            alias_value='Dan maybe?',
        )

        self.assertEqual(profile.aliases.count(), 1)
        self.assertEqual(profile.aliases.get().alias_value, 'Dan maybe?')

    def test_merge_candidates_require_distinct_people(self):
        person = Person.objects.create(full_name='Jane Smith')

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                MergeCandidate.objects.create(
                    left_person=person,
                    right_person=person,
                    confidence_score=90,
                )


class CsvImportApiTests(TestCase):
    def post_csv(self, csv_text: str, source_system: str = SourceSystem.MANUAL_CSV):
        uploaded_file = SimpleUploadedFile(
            'contacts.csv',
            csv_text.encode('utf-8'),
            content_type='text/csv',
        )
        return self.client.post(
            reverse('external-profiles-import-csv'),
            {
                'file': uploaded_file,
                'source_system': source_system,
            },
        )

    def test_csv_import_creates_external_profiles_and_summary(self):
        response = self.post_csv(
            'source_record_id,full_name,primary_email\n'
            'ext-1,Jane Smith,jane@example.com\n'
            'ext-2,David Chen,david@example.com\n'
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.json(),
            {
                'import_run_id': response.json()['import_run_id'],
                'records_received': 2,
                'records_processed': 2,
                'records_failed': 0,
            },
        )
        self.assertEqual(ExternalProfile.objects.count(), 2)
        self.assertEqual(
            ExternalProfile.objects.get(source_record_id='ext-1').source_payload_json[
                'full_name'
            ],
            'Jane Smith',
        )

    def test_csv_import_reports_row_level_failures_without_stopping_import(self):
        response = self.post_csv(
            'full_name,notes,phone\n'
            'Jane Smith,,+14155550100\n'
            ',Unknown person from old list,\n'
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['records_processed'], 1)
        self.assertEqual(response.json()['records_failed'], 1)

        import_run_response = self.client.get(
            reverse('import-run-detail', args=[response.json()['import_run_id']])
        )

        self.assertEqual(import_run_response.status_code, 200)
        self.assertEqual(import_run_response.json()['records_received'], 2)
        self.assertEqual(len(import_run_response.json()['failures']), 1)
        self.assertEqual(import_run_response.json()['failures'][0]['row_number'], 3)

    def test_csv_import_is_idempotent_when_source_record_id_repeats(self):
        first_response = self.post_csv(
            'source_record_id,full_name\n'
            'ext-1,Jane Smith\n'
        )
        second_response = self.post_csv(
            'source_record_id,full_name\n'
            'ext-1,Jane A. Smith\n'
        )

        self.assertEqual(first_response.status_code, 201)
        self.assertEqual(second_response.status_code, 201)
        self.assertEqual(ExternalProfile.objects.count(), 1)
        self.assertEqual(
            ExternalProfile.objects.get(source_record_id='ext-1').source_payload_json[
                'full_name'
            ],
            'Jane A. Smith',
        )

    def test_csv_import_rejects_unknown_source_system(self):
        response = self.post_csv(
            'source_record_id,full_name\n'
            'ext-1,Jane Smith\n',
            source_system='telegram',
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json(),
            {'error': 'Unsupported source_system: telegram'},
        )
        self.assertEqual(SyncRun.objects.count(), 0)

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from .normalization import normalize_email, normalize_name, normalize_phone
from .models import (
    CanonicalMembershipTier,
    ExternalProfile,
    ExternalProfileAlias,
    ExternalProfileGroupObservation,
    ExternalProfileSnapshot,
    FieldSourcePriority,
    MergeCandidate,
    Person,
    SourceSystem,
    SyncDirection,
    SyncRun,
    SyncRunStatus,
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

    def test_group_observation_string_falls_back_to_external_profile_id(self):
        profile = ExternalProfile.objects.create(
            source_system=SourceSystem.WHATSAPP,
            source_record_id='+819012345678',
        )
        observation = ExternalProfileGroupObservation.objects.create(
            external_profile=profile,
        )

        self.assertEqual(str(observation), str(profile.external_profile_id))


class CsvImportApiTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.staff_user = user_model.objects.create_user(
            username='staff-user',
            email='staff@example.com',
            password='not-used',
            is_staff=True,
        )
        self.non_staff_user = user_model.objects.create_user(
            username='member-user',
            email='member@example.com',
            password='not-used',
        )

    def login_staff(self):
        self.client.force_login(self.staff_user)

    def login_non_staff(self):
        self.client.force_login(self.non_staff_user)

    def post_csv(
        self,
        csv_text: str,
        source_system: str = SourceSystem.MANUAL_CSV,
        *,
        client=None,
    ):
        uploaded_file = SimpleUploadedFile(
            'contacts.csv',
            csv_text.encode('utf-8'),
            content_type='text/csv',
        )
        request_client = client or self.client
        return request_client.post(
            reverse('external-profiles-import-csv'),
            {
                'file': uploaded_file,
                'source_system': source_system,
            },
        )

    def test_csv_import_requires_authentication(self):
        response = self.post_csv(
            'source_record_id,full_name\n'
            'ext-1,Jane Smith\n'
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), {'error': 'authentication required'})
        self.assertEqual(ExternalProfile.objects.count(), 0)

    def test_csv_import_requires_staff_access(self):
        self.login_non_staff()

        response = self.post_csv(
            'source_record_id,full_name\n'
            'ext-1,Jane Smith\n'
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json(), {'error': 'staff access required'})
        self.assertEqual(ExternalProfile.objects.count(), 0)

    def test_csv_import_creates_external_profiles_and_summary(self):
        self.login_staff()

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
        self.assertEqual(ExternalProfileSnapshot.objects.count(), 2)

    def test_csv_import_reports_row_level_failures_without_stopping_import(self):
        self.login_staff()

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

    def test_import_run_detail_requires_authentication(self):
        self.login_staff()
        sync_run = SyncRun.objects.create(
            source_system=SourceSystem.MANUAL_CSV,
            direction=SyncDirection.INBOUND,
            status=SyncRunStatus.COMPLETED,
        )
        self.client.logout()

        response = self.client.get(reverse('import-run-detail', args=[sync_run.sync_run_id]))

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), {'error': 'authentication required'})

    def test_csv_import_preserves_snapshot_history_when_source_record_id_repeats(self):
        self.login_staff()

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
        profile = ExternalProfile.objects.get(source_record_id='ext-1')
        self.assertEqual(profile.source_payload_json['full_name'], 'Jane A. Smith')

        snapshots = list(profile.snapshots.order_by('created_at'))
        self.assertEqual(len(snapshots), 2)
        self.assertEqual(snapshots[0].raw_payload_json['full_name'], 'Jane Smith')
        self.assertEqual(snapshots[1].raw_payload_json['full_name'], 'Jane A. Smith')

    def test_csv_import_normalizes_identity_fields_before_deriving_source_record_id(self):
        self.login_staff()

        first_response = self.post_csv(
            'full_name,primary_email\n'
            'Jane Smith,  Jane.Smith@Example.COM  \n'
        )
        second_response = self.post_csv(
            'name,email\n'
            'Jane Smith,jane.smith@example.com\n'
        )

        self.assertEqual(first_response.status_code, 201)
        self.assertEqual(second_response.status_code, 201)
        self.assertEqual(ExternalProfile.objects.count(), 1)
        profile = ExternalProfile.objects.get()
        self.assertEqual(profile.source_record_id, 'jane.smith@example.com')
        self.assertEqual(profile.snapshots.count(), 2)
        self.assertEqual(
            profile.snapshots.order_by('created_at').first().normalized_payload_json[
                'primary_email'
            ],
            'jane.smith@example.com',
        )

    def test_csv_import_rejects_unknown_source_system(self):
        self.login_staff()

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


class OperatorAuthTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.staff_user = user_model.objects.create_user(
            username='operator',
            email='operator@example.com',
            password='StrongPassword123!',
            is_staff=True,
        )
        self.member_user = user_model.objects.create_user(
            username='member',
            email='member@example.com',
            password='StrongPassword123!',
            is_staff=False,
        )

    def test_root_redirects_anonymous_users_to_login(self):
        response = self.client.get(reverse('root'))

        self.assertRedirects(response, reverse('login'))

    def test_staff_can_log_in_and_reach_operator_home(self):
        response = self.client.post(
            reverse('login'),
            {
                'username': 'operator',
                'password': 'StrongPassword123!',
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Member data with a usable front door.')

    def test_non_staff_login_is_rejected(self):
        response = self.client.post(
            reverse('login'),
            {
                'username': 'member',
                'password': 'StrongPassword123!',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Staff access required for Member OS.')

    def test_operator_home_forbids_authenticated_non_staff_users(self):
        self.client.force_login(self.member_user)

        response = self.client.get(reverse('operator-home'))

        self.assertEqual(response.status_code, 403)

    def test_staff_can_change_password_without_admin(self):
        self.client.force_login(self.staff_user)

        response = self.client.post(
            reverse('password_change'),
            {
                'old_password': 'StrongPassword123!',
                'new_password1': 'EvenStrongerPassword456!',
                'new_password2': 'EvenStrongerPassword456!',
            },
            follow=True,
        )

        self.staff_user.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Password updated.')
        self.assertTrue(
            self.staff_user.check_password('EvenStrongerPassword456!')
        )

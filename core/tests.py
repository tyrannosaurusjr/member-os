import tempfile
import json
from pathlib import Path

from django.core.management import call_command
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from .apple_contacts import FIELD_SEPARATOR, RECORD_SEPARATOR, build_import_rows, parse_contacts_export
from .luma_export import build_import_rows as build_luma_import_rows
from .stripe_export import build_import_rows as build_stripe_import_rows
from .substack_export import build_import_rows as build_substack_import_rows
from .substack_export import parse_substack_csv
from .normalization import normalize_email, normalize_name, normalize_phone
from .models import (
    CanonicalMembershipTier,
    ExternalProfile,
    ExternalProfileAlias,
    ExternalProfileGroupObservation,
    ExternalProfileSnapshot,
    FieldSourcePriority,
    MergeAuditLog,
    MergeCandidate,
    Person,
    ProfileSyncStatus,
    ReviewItemType,
    ReviewQueueItem,
    ReviewQueueStatus,
    SourceSystem,
    SyncDirection,
    SyncEvent,
    SyncEventStatus,
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


class AppleContactsWorkflowTests(SimpleTestCase):
    def test_parse_contacts_export_reads_field_and_record_separators(self):
        raw_text = RECORD_SEPARATOR.join(
            [
                FIELD_SEPARATOR.join(
                    [
                        'contact-1',
                        'Jane Smith',
                        'Jane',
                        'Smith',
                        'jane@example.com',
                        'jsmith@work.com',
                        'jane@example.com|||jsmith@work.com',
                        '+14155550100',
                        '+14155550101',
                        '+14155550100|||+14155550101',
                        'Acme Ventures',
                        'Partner',
                        'Met at summit',
                    ]
                )
            ]
        )

        contacts = parse_contacts_export(raw_text)

        self.assertEqual(len(contacts), 1)
        self.assertEqual(contacts[0]['source_record_id'], 'contact-1')
        self.assertEqual(
            contacts[0]['emails'],
            ['jane@example.com', 'jsmith@work.com'],
        )

    def test_build_import_rows_preserves_multi_value_email_and_phone_context(self):
        rows = build_import_rows(
            [
                {
                    'source_record_id': 'contact-1',
                    'full_name': 'Jane Smith',
                    'first_name': 'Jane',
                    'last_name': 'Smith',
                    'emails': ['jane@example.com', 'jsmith@work.com'],
                    'phones': ['+14155550100', '+14155550101'],
                    'company': 'Acme Ventures',
                    'job_title': 'Partner',
                    'notes': 'Met at summit',
                }
            ]
        )

        self.assertEqual(rows[0]['primary_email'], 'jane@example.com')
        self.assertEqual(rows[0]['secondary_email'], 'jsmith@work.com')
        self.assertEqual(rows[0]['primary_phone'], '+14155550100')
        self.assertEqual(rows[0]['secondary_phone'], '+14155550101')
        self.assertEqual(rows[0]['all_emails_json'], '["jane@example.com", "jsmith@work.com"]')


class StripeWorkflowTests(SimpleTestCase):
    def test_build_import_rows_maps_customer_and_subscription_context(self):
        rows = build_stripe_import_rows(
            customers=[
                {
                    'id': 'cus_123',
                    'name': 'Jane Smith',
                    'email': 'jane@example.com',
                    'phone': '+14155550100',
                    'metadata': {
                        'company': 'Acme Ventures',
                        'title': 'Partner',
                    },
                    'description': 'Delphi member',
                    'created': 1710000000,
                    'currency': 'usd',
                    'livemode': False,
                    'delinquent': False,
                    'balance': 0,
                }
            ],
            subscriptions=[
                {
                    'id': 'sub_123',
                    'customer': 'cus_123',
                    'status': 'active',
                    'cancel_at_period_end': False,
                    'current_period_start': 1710000000,
                    'current_period_end': 1712592000,
                    'items': {
                        'data': [
                            {
                                'price': {
                                    'id': 'price_123',
                                    'product': 'prod_123',
                                    'unit_amount': 50000,
                                    'currency': 'usd',
                                    'nickname': 'Core Membership',
                                    'recurring': {
                                        'interval': 'month',
                                        'interval_count': 1,
                                    },
                                }
                            }
                        ]
                    },
                }
            ],
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['source_record_id'], 'cus_123')
        self.assertEqual(rows[0]['full_name'], 'Jane Smith')
        self.assertEqual(rows[0]['first_name'], 'Jane')
        self.assertEqual(rows[0]['last_name'], 'Smith')
        self.assertEqual(rows[0]['company'], 'Acme Ventures')
        self.assertEqual(rows[0]['job_title'], 'Partner')
        self.assertEqual(rows[0]['membership_status'], 'active')
        self.assertEqual(rows[0]['stripe_subscription_count'], '1')
        self.assertEqual(rows[0]['stripe_active_subscription_count'], '1')
        self.assertIn('Delphi member', rows[0]['notes'])
        self.assertIn('Stripe subscriptions: active x1', rows[0]['notes'])
        subscriptions_payload = json.loads(rows[0]['stripe_subscriptions_json'])
        self.assertEqual(subscriptions_payload[0]['status'], 'active')
        self.assertEqual(subscriptions_payload[0]['items'][0]['price_id'], 'price_123')

    def test_build_import_rows_falls_back_to_email_for_missing_name(self):
        rows = build_stripe_import_rows(
            customers=[
                {
                    'id': 'cus_456',
                    'email': 'ops.team@example.com',
                    'metadata': {},
                    'created': 1710000000,
                    'livemode': True,
                    'delinquent': True,
                    'balance': 1200,
                }
            ],
            subscriptions=[],
        )

        self.assertEqual(rows[0]['full_name'], 'Ops Team')
        self.assertEqual(rows[0]['first_name'], 'Ops')
        self.assertEqual(rows[0]['last_name'], 'Team')
        self.assertEqual(rows[0]['membership_status'], '')
        self.assertEqual(rows[0]['stripe_subscription_count'], '0')
        self.assertEqual(rows[0]['stripe_livemode'], 'true')
        self.assertEqual(rows[0]['stripe_delinquent'], 'true')


class LumaWorkflowTests(SimpleTestCase):
    def test_build_import_rows_groups_same_person_across_multiple_events(self):
        rows = build_luma_import_rows(
            events=[
                {
                    'api_id': 'evt_1',
                    'name': 'Delphi Dinner',
                    'start_at': '2026-03-01T10:00:00.000Z',
                },
                {
                    'api_id': 'evt_2',
                    'name': 'Founder Breakfast',
                    'start_at': '2026-03-10T10:00:00.000Z',
                },
            ],
            guests_by_event={
                'evt_1': [
                    {
                        'api_id': 'gst_1',
                        'approval_status': 'approved',
                        'registered_at': '2026-02-20T10:00:00.000Z',
                        'user': {
                            'api_id': 'usr_1',
                            'name': 'Jane Smith',
                            'email': 'jane@example.com',
                        },
                    }
                ],
                'evt_2': [
                    {
                        'api_id': 'gst_2',
                        'approval_status': 'approved',
                        'registered_at': '2026-03-05T10:00:00.000Z',
                        'user': {
                            'api_id': 'usr_1',
                            'name': 'Jane Smith',
                            'email': 'jane@example.com',
                        },
                    }
                ],
            },
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['source_record_id'], 'usr_1')
        self.assertEqual(rows[0]['full_name'], 'Jane Smith')
        self.assertEqual(rows[0]['luma_person_id'], 'usr_1')
        self.assertEqual(rows[0]['luma_guest_count'], '2')
        self.assertEqual(rows[0]['luma_event_count'], '2')
        self.assertEqual(rows[0]['luma_last_registered_at'], '2026-03-05T10:00:00.000Z')
        self.assertEqual(
            json.loads(rows[0]['luma_event_names_json']),
            ['Delphi Dinner', 'Founder Breakfast'],
        )
        self.assertEqual(
            json.loads(rows[0]['luma_approval_statuses_json']),
            ['approved'],
        )
        self.assertIn('Luma guest history across 2 registration(s)', rows[0]['notes'])

    def test_build_import_rows_falls_back_to_email_when_user_id_missing(self):
        rows = build_luma_import_rows(
            events=[
                {
                    'api_id': 'evt_3',
                    'name': 'Community Salon',
                    'start_at': '2026-03-15T10:00:00.000Z',
                }
            ],
            guests_by_event={
                'evt_3': [
                    {
                        'api_id': 'gst_3',
                        'approval_status': 'invited',
                        'registered_at': '2026-03-12T10:00:00.000Z',
                        'user': {
                            'name': 'Ops Team',
                            'email': 'ops@example.com',
                        },
                    }
                ]
            },
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['source_record_id'], 'ops@example.com')
        self.assertEqual(rows[0]['primary_email'], 'ops@example.com')
        self.assertEqual(rows[0]['full_name'], 'Ops Team')
        self.assertEqual(rows[0]['first_name'], 'Ops')
        self.assertEqual(rows[0]['last_name'], 'Team')


class SubstackWorkflowTests(SimpleTestCase):
    def test_parse_substack_csv_normalizes_common_headers(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            csv_path = Path(temp_dir) / 'substack.csv'
            csv_path.write_text(
                'Email,Name,Status,Subscription Type,Subscribed At\n'
                'jane@example.com,Jane Smith,active,paid,2026-03-01\n',
                encoding='utf-8',
            )

            rows = parse_substack_csv(csv_path)

        self.assertEqual(
            rows,
            [
                {
                    'email': 'jane@example.com',
                    'full_name': 'Jane Smith',
                    'status': 'active',
                    'subscription_type': 'paid',
                    'subscribed_at': '2026-03-01',
                }
            ],
        )

    def test_build_import_rows_maps_substack_subscriber_context(self):
        rows = build_substack_import_rows(
            [
                {
                    'subscriber_id': 'sub_123',
                    'email': 'jane@example.com',
                    'full_name': 'Jane Smith',
                    'status': 'active',
                    'subscription_type': 'paid',
                    'subscribed_at': '2026-03-01',
                    'notes': 'Imported from newsletter',
                }
            ]
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['source_record_id'], 'sub_123')
        self.assertEqual(rows[0]['first_name'], 'Jane')
        self.assertEqual(rows[0]['last_name'], 'Smith')
        self.assertEqual(rows[0]['membership_status'], 'active')
        self.assertEqual(rows[0]['substack_subscription_status'], 'active')
        self.assertEqual(rows[0]['substack_subscription_type'], 'paid')
        self.assertIn('Imported from newsletter', rows[0]['notes'])

    def test_build_import_rows_falls_back_to_email_when_subscriber_id_missing(self):
        rows = build_substack_import_rows(
            [
                {
                    'email': 'ops@example.com',
                    'first_name': 'Ops',
                    'last_name': 'Team',
                    'status': 'unsubscribed',
                    'subscription_type': 'free',
                }
            ]
        )

        self.assertEqual(rows[0]['source_record_id'], 'ops@example.com')
        self.assertEqual(rows[0]['full_name'], 'Ops Team')
        self.assertEqual(rows[0]['membership_status'], 'inactive')


class ImportExternalProfilesCommandTests(TestCase):
    def test_management_command_imports_csv_from_filesystem(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            csv_path = Path(temp_dir) / 'apple_contacts.csv'
            csv_path.write_text(
                'source_record_id,full_name,primary_email\n'
                'contact-1,Jane Smith,jane@example.com\n',
                encoding='utf-8',
            )

            call_command(
                'import_external_profiles_csv',
                str(csv_path),
                source_system=SourceSystem.APPLE_CONTACTS,
            )

        self.assertEqual(ExternalProfile.objects.count(), 1)
        self.assertEqual(
            ExternalProfile.objects.get().source_system,
            SourceSystem.APPLE_CONTACTS,
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
        self.assertEqual(priorities[('membership_status', SourceSystem.SUBSTACK)], 5)
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

    def test_external_profile_accepts_substack_source_system(self):
        profile = ExternalProfile.objects.create(
            source_system=SourceSystem.SUBSTACK,
            source_record_id='sub_123',
        )

        self.assertEqual(profile.source_system, SourceSystem.SUBSTACK)

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

    def test_csv_import_creates_open_profile_review_items_for_unlinked_profiles(self):
        self.login_staff()

        response = self.post_csv(
            'source_record_id,full_name,primary_email\n'
            'ext-1,Jane Smith,jane@example.com\n'
        )

        self.assertEqual(response.status_code, 201)
        review_item = ReviewQueueItem.objects.get()
        self.assertEqual(review_item.item_type, ReviewItemType.PROFILE_LINK_REVIEW)
        self.assertEqual(review_item.status, ReviewQueueStatus.OPEN)
        self.assertEqual(
            review_item.related_external_profile.source_record_id,
            'ext-1',
        )

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

    def test_staff_can_import_csv_from_operator_home(self):
        self.client.force_login(self.staff_user)

        response = self.client.post(
            reverse('operator-home'),
            {
                'source_system': SourceSystem.MANUAL_CSV,
                'file': SimpleUploadedFile(
                    'operators.csv',
                    (
                        'source_record_id,full_name,primary_email\n'
                        'ext-101,Jane Smith,jane@example.com\n'
                    ).encode('utf-8'),
                    content_type='text/csv',
                ),
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Import complete: 1 processed, 0 failed.')
        self.assertContains(response, 'Import Workspace')
        self.assertEqual(ExternalProfile.objects.count(), 1)
        self.assertEqual(SyncRun.objects.count(), 1)

    def test_operator_home_shows_selected_run_failures(self):
        self.client.force_login(self.staff_user)
        sync_run = SyncRun.objects.create(
            source_system=SourceSystem.MANUAL_CSV,
            direction=SyncDirection.INBOUND,
            status=SyncRunStatus.COMPLETED,
            records_processed=1,
            records_failed=1,
            error_summary='1 row failed during import.',
        )
        SyncEvent.objects.create(
            sync_run=sync_run,
            source_system=SourceSystem.MANUAL_CSV,
            action_type='csv_import_row',
            payload={
                'row_number': 3,
                'row': {'full_name': ''},
                'source_record_id': 'ext-404',
            },
            status=SyncEventStatus.ERROR,
            error_message='Row is missing an identity hint.',
        )

        response = self.client.get(reverse('operator-home'), {'run': sync_run.sync_run_id})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '1 row failed during import.')
        self.assertContains(response, 'Row 3')
        self.assertContains(response, 'Row is missing an identity hint.')

    def test_staff_can_download_sample_import_template(self):
        self.client.force_login(self.staff_user)

        response = self.client.get(reverse('sample-import-csv-template'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        self.assertIn('attachment; filename="member-os-sample-import.csv"', response['Content-Disposition'])
        self.assertIn('source_record_id,full_name,primary_email', response.content.decode('utf-8'))

    def test_people_directory_lists_people_and_unlinked_profiles(self):
        self.client.force_login(self.staff_user)
        person = Person.objects.create(
            full_name='Jane Smith',
            primary_email='jane@example.com',
            company='Acme Ventures',
        )
        ExternalProfile.objects.create(
            person=person,
            source_system=SourceSystem.MANUAL_CSV,
            source_record_id='ext-linked',
        )
        ExternalProfile.objects.create(
            source_system=SourceSystem.MANUAL_CSV,
            source_record_id='ext-unlinked',
            source_payload_json={'full_name': 'Unlinked Person'},
        )

        response = self.client.get(reverse('people-directory'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'People directory and import triage.')
        self.assertContains(response, 'Jane Smith')
        self.assertContains(response, 'Unlinked Person')

    def test_people_directory_search_filters_results(self):
        self.client.force_login(self.staff_user)
        Person.objects.create(full_name='Jane Smith', company='Acme Ventures')
        Person.objects.create(full_name='David Chen', company='Summit Capital')

        response = self.client.get(reverse('people-directory'), {'q': 'Acme'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Jane Smith')
        self.assertNotContains(response, 'David Chen')

    def test_person_detail_shows_linked_profiles_and_snapshots(self):
        self.client.force_login(self.staff_user)
        person = Person.objects.create(
            full_name='Jane Smith',
            primary_email='jane@example.com',
            company='Acme Ventures',
        )
        profile = ExternalProfile.objects.create(
            person=person,
            source_system=SourceSystem.MANUAL_CSV,
            source_record_id='ext-123',
            source_payload_json={'full_name': 'Jane Smith'},
        )
        ExternalProfileSnapshot.objects.create(
            external_profile=profile,
            raw_payload_json={'full_name': 'Jane Smith'},
            normalized_payload_json={'full_name': 'Jane Smith'},
        )

        response = self.client.get(reverse('person-detail', args=[person.person_id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Canonical person record with linked external profiles')
        self.assertContains(response, 'ext-123')
        self.assertContains(response, 'Raw payload')

    def test_review_queue_lists_open_profile_link_items(self):
        self.client.force_login(self.staff_user)
        profile = ExternalProfile.objects.create(
            source_system=SourceSystem.MANUAL_CSV,
            source_record_id='ext-review-1',
            source_payload_json={'full_name': 'Queued Person'},
        )
        ReviewQueueItem.objects.create(
            item_type=ReviewItemType.PROFILE_LINK_REVIEW,
            related_external_profile=profile,
            title='Link or create person for Queued Person',
            status=ReviewQueueStatus.OPEN,
        )

        response = self.client.get(reverse('review-queue'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Profiles waiting for operator judgment.')
        self.assertContains(response, 'Queued Person')

    def test_profile_review_create_person_action_creates_person_and_resolves_review_item(self):
        self.client.force_login(self.staff_user)
        profile = ExternalProfile.objects.create(
            source_system=SourceSystem.MANUAL_CSV,
            source_record_id='ext-create-1',
            source_payload_json={
                'full_name': 'Created Person',
                'primary_email': 'created@example.com',
                'company': 'Acme Ventures',
            },
        )
        ExternalProfileSnapshot.objects.create(
            external_profile=profile,
            raw_payload_json=profile.source_payload_json,
            normalized_payload_json=profile.source_payload_json,
        )
        review_item = ReviewQueueItem.objects.create(
            item_type=ReviewItemType.PROFILE_LINK_REVIEW,
            related_external_profile=profile,
            title='Link or create person for Created Person',
            status=ReviewQueueStatus.OPEN,
        )

        response = self.client.post(
            reverse('profile-create-person', args=[profile.external_profile_id]),
            follow=True,
        )

        profile.refresh_from_db()
        review_item.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Person.objects.count(), 1)
        person = Person.objects.get()
        self.assertEqual(person.full_name, 'Created Person')
        self.assertEqual(profile.person, person)
        self.assertEqual(profile.sync_status, ProfileSyncStatus.SYNCED)
        self.assertEqual(review_item.status, ReviewQueueStatus.RESOLVED)
        self.assertEqual(MergeAuditLog.objects.count(), 1)
        self.assertContains(response, 'Created canonical person Created Person')

    def test_profile_review_link_person_action_links_existing_person_and_resolves_review_item(self):
        self.client.force_login(self.staff_user)
        person = Person.objects.create(
            full_name='Jane Smith',
            primary_email='jane@example.com',
        )
        profile = ExternalProfile.objects.create(
            source_system=SourceSystem.MANUAL_CSV,
            source_record_id='ext-link-1',
            source_payload_json={
                'full_name': 'Jane Smith',
                'primary_email': 'jane@example.com',
                'company': 'Acme Ventures',
            },
        )
        ExternalProfileSnapshot.objects.create(
            external_profile=profile,
            raw_payload_json=profile.source_payload_json,
            normalized_payload_json=profile.source_payload_json,
        )
        review_item = ReviewQueueItem.objects.create(
            item_type=ReviewItemType.PROFILE_LINK_REVIEW,
            related_external_profile=profile,
            title='Link or create person for Jane Smith',
            status=ReviewQueueStatus.OPEN,
        )

        response = self.client.post(
            reverse('profile-link-person', args=[profile.external_profile_id]),
            {'person_id': str(person.person_id)},
            follow=True,
        )

        profile.refresh_from_db()
        person.refresh_from_db()
        review_item.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(profile.person, person)
        self.assertEqual(profile.sync_status, ProfileSyncStatus.SYNCED)
        self.assertEqual(person.company, 'Acme Ventures')
        self.assertEqual(review_item.status, ReviewQueueStatus.RESOLVED)
        self.assertEqual(MergeAuditLog.objects.count(), 1)
        self.assertContains(response, 'Linked Manual CSV profile ext-link-1 to Jane Smith.')

# Schema Deviations

This document records the intentional differences between the original [`database_schema.sql`](/Users/mkultraman/Desktop/member-os/database_schema.sql) design and the first Django/PostgreSQL implementation.

## 1. UUID Generation

The SQL schema uses `uuid_generate_v4()` from the `uuid-ossp` extension.

The Django implementation uses `UUIDField(default=uuid.uuid4)` instead. This preserves UUID primary keys without requiring `uuid-ossp` in every environment.

## 2. Django-Managed Timestamps

Tables with `created_at` and `updated_at` now use Django-managed timestamp fields (`auto_now_add` and `auto_now`) instead of pure database defaults.

This keeps the app-level write path simple for the first implementation. If we later need database-side triggers for synchronization workloads, we can add them deliberately.

## 3. Expanded Source Systems

The original SQL source-system enum was extended to include:

- `whatsapp`
- `linkedin`
- `clay`

This reflects the agreed product direction: Member OS is the canonical system of record, while WhatsApp, LinkedIn, Clay, and the existing operational tools are evidence sources or sync targets.

## 4. WhatsApp Identity Evidence Tables

Two new tables were added:

- `external_profile_aliases`
- `external_profile_group_observations`

These support the WhatsApp rectification workflow by preserving:

- phone-only external profiles
- multiple observed aliases over time
- group-context evidence without treating group membership as canonical identity

## 5. Review and Audit Extensions

The original review and audit enums were expanded with WhatsApp-aware values:

- review item types now include `unknown_whatsapp_identity` and `alias_conflict`
- merge audit decisions now include `identity_rectification`

These additions make ambiguous identity work first-class instead of forcing it into unrelated review categories.

## 6. Additional Integrity Guardrails

The Django schema adds a few database constraints that were not explicit in the original SQL:

- confidence and percentage fields are constrained to `0-100`
- merge candidates must reference two distinct people
- merge candidate signal counts must be non-negative

These are protective constraints that align with the intended meaning of the data.


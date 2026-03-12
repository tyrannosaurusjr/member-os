# Delphi Member OS
## API Specification

Base URL: `/api/v1`

Authentication: Bearer token or session-based admin auth

Response format: JSON

---

## 1. Health and System

### GET /health
Returns service health.

Response:
```json
{
  "status": "ok"
}
```

### GET /system/summary
Returns dashboard summary counts.

Response fields:
- total_persons
- total_memberships
- unresolved_duplicates
- unknown_tiers
- sync_errors
- last_successful_sync_by_source

---

## 2. Persons

### GET /persons
List canonical persons.

Query params:
- search
- email
- company
- membership_status
- canonical_tier_id
- page
- page_size

### GET /persons/{person_id}
Fetch a single canonical person, including:
- profile fields
- memberships
- external profiles
- review items

### POST /persons
Create a canonical person manually.

Request body:
```json
{
  "full_name": "Jane Smith",
  "primary_email": "jane@example.com",
  "company": "Alpha Capital"
}
```

### PATCH /persons/{person_id}
Update canonical person fields.

### POST /persons/{person_id}/merge
Manually merge another person into this canonical person.

Request body:
```json
{
  "source_person_id": "uuid",
  "reason": "Confirmed duplicate by admin"
}
```

### POST /persons/{person_id}/split
Split a record if a previous merge was wrong.

Request body:
```json
{
  "reason": "Two people were incorrectly merged"
}
```

---

## 3. External Profiles

### GET /external-profiles
List external profiles.

Query params:
- source_system
- person_id
- sync_status

### GET /external-profiles/{external_profile_id}
View source payload and normalized representation.

### POST /external-profiles/import/csv
Upload a CSV file for Apple Contacts or manual records.

Multipart form data:
- file

Response:
- import_run_id
- records_received

---

## 4. Membership Tiers

### GET /tiers
List canonical membership tiers.

### POST /tiers
Create canonical tier.

Request body:
```json
{
  "canonical_tier_name": "Core Member",
  "tier_family": "Paid Individual",
  "description": "Standard paid member tier"
}
```

### PATCH /tiers/{canonical_tier_id}
Update canonical tier.

### GET /tier-aliases
List alias mappings.

Query params:
- source_system
- canonical_tier_id

### POST /tier-aliases
Create alias mapping.

Request body:
```json
{
  "source_system": "stripe",
  "source_tier_name": "Delphi Circle",
  "source_product_id": "prod_123",
  "canonical_tier_id": "uuid",
  "confidence_score": 92
}
```

### PATCH /tier-aliases/{alias_id}
Update alias mapping.

---

## 5. Memberships

### GET /memberships
List memberships.

Query params:
- person_id
- canonical_tier_id
- status
- payment_method_type
- review_required

### GET /memberships/{membership_id}
Fetch membership details.

### POST /memberships
Create membership.

Request body:
```json
{
  "person_id": "uuid",
  "canonical_tier_id": "uuid",
  "status": "active",
  "payment_method_type": "bank_transfer",
  "price_paid": 150000,
  "price_currency": "JPY",
  "list_price_snapshot": 250000,
  "discount_reason": "Legacy pricing"
}
```

### PATCH /memberships/{membership_id}
Update membership record.

### POST /memberships/{membership_id}/seats
Create a corporate seat relationship.

Request body:
```json
{
  "membership_holder_person_id": "uuid",
  "seat_holder_person_id": "uuid",
  "seat_title": "Assistant"
}
```

---

## 6. Matching and Merge Review

### GET /merge-candidates
List potential duplicates.

Query params:
- status
- min_confidence
- recommended_action

### POST /matching/run
Run matching engine.

Optional request body:
```json
{
  "person_ids": ["uuid1", "uuid2"]
}
```

### GET /merge-candidates/{merge_candidate_id}
View a merge candidate and its explanation.

### POST /merge-candidates/{merge_candidate_id}/approve
Approve merge.

Request body:
```json
{
  "performed_by": "admin@example.com",
  "reason": "Same email and company"
}
```

### POST /merge-candidates/{merge_candidate_id}/reject
Reject merge.

### POST /merge-candidates/{merge_candidate_id}/ignore
Ignore candidate.

---

## 7. Review Queue

### GET /review-queue
List review items.

Query params:
- item_type
- severity
- status
- assigned_to

### GET /review-queue/{review_item_id}
Fetch a review item.

### PATCH /review-queue/{review_item_id}
Update review item status.

Request body:
```json
{
  "status": "in_progress",
  "assigned_to": "admin@example.com"
}
```

### POST /review-queue/{review_item_id}/resolve
Resolve a review item.

Request body:
```json
{
  "resolution_note": "Mapped unknown tier to Core Member"
}
```

---

## 8. Sync

### POST /sync/run
Start a sync.

Request body:
```json
{
  "source_system": "mailchimp",
  "direction": "outbound",
  "dry_run": true
}
```

### GET /sync/runs
List sync runs.

### GET /sync/runs/{sync_run_id}
Fetch sync run detail.

### GET /sync/events
List sync events.

Query params:
- sync_run_id
- source_system
- status

---

## 9. Connectors

### POST /connectors/stripe/test
Test Stripe credentials.

### POST /connectors/mailchimp/test
Test Mailchimp credentials.

### POST /connectors/luma/test
Test Luma credentials.

### POST /connectors/google-sheets/test
Test Google Sheets credentials.

### POST /connectors/{source_system}/pull
Pull fresh data from a source.

Request body:
```json
{
  "full_refresh": false
}
```

---

## 10. Exports

### GET /exports/persons.csv
Export canonical persons as CSV.

### GET /exports/memberships.csv
Export canonical memberships as CSV.

### GET /exports/review-queue.csv
Export unresolved review items as CSV.

---

## 11. Audit Logs

### GET /audit/merges
List merge audit logs.

### GET /audit/merges/{decision_id}
Fetch a single merge audit record.

---

## 12. Suggested Permission Model

### Admin
- full CRUD
- approve merges
- run syncs
- manage connectors
- update tiers

### Operator
- view records
- edit records
- resolve review items
- run limited syncs

### Viewer
- read-only access
- export access if permitted

# Delphi Member OS
## System Architecture

## 1. Purpose

This document explains the recommended architecture for Delphi Member OS, a contact rectification and membership normalization platform built to clean, verify, standardize, and synchronize member data across the Delphi Network's tools.

The architecture assumes an initial internal deployment for The Delphi Network, with the system designed in a way that can later become a multi-tenant SaaS product for other membership organizations.

---

## 2. Architectural Principles

### Canonical Source of Truth
All external systems are treated as inputs and outputs, not as the final authority. The platform maintains its own canonical view of:
- person identity
- organization relationships
- membership status
- membership tier
- payment method
- price paid

### Controlled Human Review
The system should automate obvious cases and escalate ambiguous cases. It must not silently rewrite records with low confidence.

### Tier and Price Are Separate
Membership tier is not the same thing as price paid. Discounting, negotiated pricing, and complimentary memberships are expected and must be supported explicitly.

### Auditability
Every meaningful merge, remap, override, and sync action must be traceable.

### Productizability
The internal architecture should avoid hardcoding Delphi-specific assumptions wherever possible.

---

## 3. High-Level Components

### 3.1 Ingestion Layer
Responsible for pulling data from:
- Stripe
- Luma
- Mailchimp
- Google Sheets
- Apple Contacts export files
- future connectors

Responsibilities:
- authenticate with external APIs
- fetch raw records
- preserve source record IDs
- store raw payloads
- schedule refreshes
- receive webhook events where available

### 3.2 Normalization Layer
Responsible for converting source-specific payloads into a normalized internal format.

Responsibilities:
- standardize names
- normalize emails
- normalize phone numbers
- normalize dates and currencies
- flatten source fields into consistent internal structures
- preserve raw source payload alongside normalized outputs

### 3.3 Identity Resolution Engine
Responsible for determining whether multiple external records represent the same person.

Responsibilities:
- exact matching on strong fields
- weighted scoring for partial matches
- generate merge candidates
- auto-merge high-confidence cases
- route uncertain cases to review queue

### 3.4 Membership Normalization Layer
Responsible for turning chaotic tier names and payment patterns into coherent canonical memberships.

Responsibilities:
- map source tier aliases to canonical tiers
- separate tier from price paid
- classify payment method
- determine active/inactive/past_due/manual states
- identify pricing anomalies
- handle corporate seats

### 3.5 Admin Dashboard
Primary operational interface for staff.

Responsibilities:
- browse canonical members
- review duplicates
- map unknown tiers
- inspect sync errors
- override fields where necessary
- export cleaned records

### 3.6 Outbound Sync Engine
Responsible for publishing cleaned records back to selected downstream systems.

Responsibilities:
- transform canonical records into destination-specific formats
- write back safe fields
- avoid destructive overwrites by default
- log all sync events
- retry failed pushes

---

## 4. Data Flow

### Step 1: Ingest
The system pulls records from each source. Each record is stored with:
- source system
- source record ID
- raw payload
- last seen timestamp

### Step 2: Normalize
Each source payload is normalized into a standard internal intermediate representation.

### Step 3: Resolve Identity
The match engine compares incoming records to canonical people and scores likely matches.

### Step 4: Normalize Membership
Tier aliases, payment evidence, and pricing data are evaluated to determine the best canonical membership representation.

### Step 5: Review
Records with uncertainty or conflict are placed into a review queue.

### Step 6: Publish
Approved and cleaned records are synced out to external systems.

---

## 5. Proposed Stack

### Backend
FastAPI or Django

Recommendation:
- Django if rapid internal admin tooling is the priority
- FastAPI if API-first architecture and modular services are the priority

### Frontend
Next.js with React

### Database
PostgreSQL

Reasons:
- robust relational modeling
- JSONB support for raw payloads
- trigram similarity for fuzzy matching
- reliable production maturity

### Queue / Background Jobs
Redis + Celery

Use cases:
- scheduled ingestion
- webhook processing
- match scoring
- outbound sync jobs
- retry handling

### Authentication
Google OAuth with role-based access control

### Hosting
Railway, Render, or Fly.io for early deployment

---

## 6. Service Boundaries

### 6.1 Connector Services
One module per source system:
- stripe_connector
- luma_connector
- mailchimp_connector
- sheets_connector
- apple_contacts_importer

Each should expose:
- full import
- incremental sync
- record fetch by ID
- webhook handler if relevant
- outbound update methods where supported

### 6.2 Matching Service
Encapsulates:
- confidence scoring
- strong/medium/weak signal evaluation
- candidate generation
- merge proposal logic

### 6.3 Membership Service
Encapsulates:
- tier alias resolution
- price/list-price logic
- discount calculations
- status derivation
- corporate seat relationships

### 6.4 Sync Service
Encapsulates:
- outbound transformations
- destination write policies
- sync logging
- conflict handling
- retries

---

## 7. Source-Specific Considerations

### Stripe
Best source for:
- automated subscription status
- recurring billing evidence
- invoices and payment timestamps

Use webhooks for:
- customer updates
- subscription updates
- invoice payments
- cancellations

### Luma
Best source for:
- event attendance
- event recency
- active engagement signals

### Mailchimp
Best source for:
- communication segmentation
- opt-in state
- tags and merge fields

### Google Sheets
Best source for:
- manual overrides
- bank transfer records
- legacy operational notes

### Apple Contacts
Best source for:
- phone numbers
- manually maintained relationship details
- companies and titles in some cases

---

## 8. Field Source Precedence

Precedence should be field-specific, not global.

Recommended examples:

### Email
1. Stripe
2. Mailchimp
3. Luma
4. Google Sheets
5. Apple Contacts

### Phone
1. Apple Contacts
2. Google Sheets
3. Stripe

### Company
1. Apple Contacts
2. Google Sheets
3. Mailchimp

### Membership Status
1. Stripe active subscription
2. Verified bank transfer in Sheets
3. Admin override
4. Mailchimp tag

---

## 9. Review Queue Design

The review queue must support these item types:
- duplicate_contact
- unknown_tier
- conflicting_membership
- missing_email
- multiple_stripe_customers
- price_anomaly
- sync_error

Each item should include:
- issue title
- severity
- related canonical person if applicable
- related membership if applicable
- relevant source records
- suggested action
- action history

---

## 10. Deployment Strategy

### Phase 1
- read-only ingestion
- canonical database
- duplicate review
- membership normalization
- exports only

### Phase 2
- Mailchimp write-back
- Google Sheets write-back

### Phase 3
- Stripe metadata updates
- Luma membership-related updates where appropriate

### Phase 4
- webhook-driven near-real-time sync
- expanded monitoring
- multi-tenant refactor if needed

---

## 11. Observability

The platform should include:
- sync run logs
- sync event logs
- failed API call records
- dashboard indicators for stale connectors
- counters for unresolved review items
- counters for unknown tiers
- counters for likely duplicates

---

## 12. Risks

### Operational Taxonomy Drift
Dan changes tier names and prices frequently.

Mitigation:
- tier alias table
- price schedules with effective dates
- unknown tier review alerts

### False Merges
Aggressive matching could merge the wrong people.

Mitigation:
- confidence thresholds
- human review for medium confidence matches
- full audit logs
- undo capability

### Overwriting Good Data
Blind write-back could damage downstream systems.

Mitigation:
- phased sync rollout
- field-level write rules
- dry-run mode
- sync logs

---

## 13. Long-Term Product Path

To support future commercialization, the architecture should later support:
- organizations / tenants
- per-tenant connector configs
- per-tenant tier taxonomies
- per-tenant match rule tuning
- usage metering
- billing and subscription management for the product itself

The initial Delphi deployment should still be built with this future in mind.

---

## 14. Recommended Next Build Order

1. Database schema
2. Stripe + Google Sheets ingestion
3. Canonical member explorer
4. Matching engine
5. Membership normalization
6. Review queue
7. Mailchimp + Luma connectors
8. Outbound sync
9. Monitoring and admin controls

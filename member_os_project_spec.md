# Member OS

## Contact Rectification and Membership Normalization Platform

Author: Matt Ketchum\
Use Case: Membership organization with fragmented systems\
Document Type: Product & Technical Specification\
Version: 1.0

------------------------------------------------------------------------

# 1. Overview

The target organization operates across multiple digital platforms that each
contain contact and membership data. These platforms include:

-   Stripe
-   Luma
-   Mailchimp
-   Google Sheets
-   Apple Contacts
-   Manual records

Over time, these systems have accumulated inconsistent and duplicated
records. Membership tiers are frequently renamed, pricing is
inconsistent due to discounts, and payments are handled through both
automated subscriptions and manual transfers.

The result is fragmented operational data that prevents accurate
understanding of:

-   Who the members actually are
-   What tier they belong to
-   How much they pay
-   Their engagement with events and the network

The purpose of this platform is to establish a **canonical database of
people and memberships** and synchronize this cleaned dataset back to
external systems.

This platform will serve as a **Member Operating System (Member OS)**.

------------------------------------------------------------------------

# 2. Core Objectives

## Primary Goals

1.  Centralize all contact records
2.  Eliminate duplicate contacts
3.  Normalize membership tiers
4.  Track payment status accurately
5.  Establish a single source of truth
6.  Synchronize corrected records back to external systems

## Secondary Goals

-   Reduce manual administrative work
-   Improve segmentation for events and communications
-   Enable accurate revenue insights
-   Create a product that can later be sold to other membership
    organizations

------------------------------------------------------------------------

# 3. Systems Being Integrated

## Stripe

Stripe contains subscription data and automated payments.

Data to ingest: - Customers - Subscriptions - Invoices - Metadata

## Luma

Luma manages events and attendee lists.

Data to ingest: - Event attendees - Event participation history - Member
flags

## Mailchimp

Mailchimp manages email communication lists.

Data to ingest: - Audience members - Tags - Merge fields - Subscription
status

## Google Sheets

Manual administrative data.

Examples: - Bank transfers - Internal member lists - Notes and
annotations

## Apple Contacts

Personal contact database maintained by the operator.

Initial ingestion approach: CSV export.

Future approach: CardDAV integration.

------------------------------------------------------------------------

# 4. System Architecture

External Systems

Stripe\
Luma\
Mailchimp\
Google Sheets\
Apple Contacts

↓

Data Ingestion Layer

↓

Normalization Engine

↓

Identity Resolution Engine

↓

Canonical Database (PostgreSQL)

↓

Membership Normalization Layer

↓

Admin Dashboard + Review Queue

↓

Outbound Sync Engine

↓

External Systems Updated

------------------------------------------------------------------------

# 5. Technology Stack

Backend: FastAPI or Django

Frontend: React / Next.js

Database: PostgreSQL

Queue / Jobs: Redis + Celery

Infrastructure: Railway / Render / Fly.io

Authentication: Google OAuth

------------------------------------------------------------------------

# 6. Canonical Data Model

## Person

Canonical representation of a contact.

Fields:

-   person_id
-   first_name
-   last_name
-   full_name
-   primary_email
-   secondary_emails
-   primary_phone
-   secondary_phones
-   company
-   job_title
-   location
-   linkedin_url
-   website
-   notes
-   created_at
-   updated_at

------------------------------------------------------------------------

## External Profile

Links canonical people to source systems.

Fields:

-   external_profile_id
-   person_id
-   source_system
-   source_record_id
-   source_payload_json
-   last_synced_at
-   sync_status

------------------------------------------------------------------------

## Canonical Membership Tier

Fields:

-   canonical_tier_id
-   canonical_tier_name
-   tier_family
-   description
-   active

Example tiers:

-   Core Member
-   Corporate Member
-   Complimentary
-   Prospect

------------------------------------------------------------------------

## Tier Alias Mapping

Maps inconsistent tier names to canonical tiers.

Fields:

-   alias_id
-   source_system
-   source_tier_name
-   source_product_id
-   source_price
-   canonical_tier_id
-   confidence_score
-   effective_from
-   effective_to

Example:

Stripe tier "Founding Circle"\
→ Canonical tier "Core Member"

------------------------------------------------------------------------

# 7. Membership Model

Membership tier and price must be treated separately.

Tier ≠ Price

Members frequently receive discounts or pay negotiated prices.

Fields:

-   membership_id
-   person_id
-   canonical_tier_id
-   status
-   payment_method_type

Pricing fields:

-   price_paid
-   currency
-   discount_percent
-   discount_reason
-   list_price_snapshot

Dates:

-   start_date
-   renewal_date
-   last_payment_date

Operational fields:

-   source_of_truth
-   review_required

------------------------------------------------------------------------

# 8. Discount Handling

Discounting is common in membership organizations with negotiated pricing.

The system must track:

Actual price paid\
List price at time of purchase\
Discount percentage\
Reason for discount

Example:

Tier: Core Member\
List Price: ¥250,000\
Price Paid: ¥150,000\
Discount: 40%\
Reason: Early supporter

------------------------------------------------------------------------

# 9. Membership Relationships

Corporate memberships may include multiple seats.

Example:

Company pays for membership.

Seats:

-   CEO
-   Assistant
-   Associate

Fields required:

-   organization_id
-   organization_name
-   membership_holder_person_id
-   seat_holder_person_id

------------------------------------------------------------------------

# 10. Identity Resolution Engine

The platform must detect duplicate contacts using confidence scoring.

## Strong Signals (95+)

-   Exact email match
-   Exact phone match
-   Stripe customer email match
-   Luma registration email match

Auto merge.

## Medium Signals (75--94)

-   Same name + same company
-   Similar email domain
-   Minor spelling differences

Sent to review queue.

## Weak Signals (\<75)

-   Similar names only
-   Same company only
-   Same location only

Do not merge automatically.

------------------------------------------------------------------------

# 11. Review Queue

Human review is required for:

-   Possible duplicate contacts
-   Unknown tier aliases
-   Conflicting membership status
-   Missing email addresses
-   Multiple Stripe customers

Admin interface must support:

Approve merge\
Reject merge\
Split record\
Map tier alias

------------------------------------------------------------------------

# 12. Synchronization Strategy

## Phase 1

Read-only ingestion.

Manual review.

No writes to external systems.

## Phase 2

Write updates to:

Mailchimp\
Google Sheets

## Phase 3

Write updates to:

Stripe metadata\
Luma membership flags

## Phase 4

Real-time sync via webhooks.

------------------------------------------------------------------------

# 13. Admin Dashboard

## Member Explorer

Searchable canonical member list.

Fields displayed:

-   name
-   email
-   membership tier
-   payment status
-   organization

## Duplicate Review

Displays potential duplicates with confidence scores.

## Tier Mapping

Admin tool to map new tier names to canonical tiers.

## Sync Monitor

Displays API errors and last sync timestamps.

------------------------------------------------------------------------

# 14. Security

Role levels:

Admin\
Operator\
Viewer

Security measures:

-   encrypted database
-   API key protection
-   audit logging

------------------------------------------------------------------------

# 15. Phase 1 Feature Scope

Version 1 must include:

-   Stripe connector
-   Mailchimp connector
-   Luma connector
-   Google Sheets connector
-   canonical database
-   duplicate detection
-   membership normalization
-   tier alias mapping
-   review queue
-   Mailchimp write-back
-   Google Sheets write-back

------------------------------------------------------------------------

# 16. Phase 2 Features

Future improvements:

-   Apple Contacts sync
-   company enrichment
-   LinkedIn enrichment
-   relationship graphs
-   analytics dashboards
-   real-time synchronization
-   multi-tenant architecture

------------------------------------------------------------------------

# 17. Development Timeline

Week 1--2 Database schema and ingestion pipelines

Week 3--4 Identity resolution engine

Week 5 Membership normalization logic

Week 6 Admin dashboard

Week 7 Synchronization engine

Week 8 Testing and deployment

------------------------------------------------------------------------

# 18. Success Metrics

Success will be measured by:

Reduction in duplicate contacts\
Accurate membership status\
Reduced manual administrative work\
Consistent data across Stripe, Mailchimp, and Luma

------------------------------------------------------------------------

# 19. Long-Term Vision

Member OS can evolve into a SaaS platform for:

-   founder networks
-   venture communities
-   professional associations
-   private clubs
-   conference ecosystems

Many organizations suffer from the same operational problems:

Fragmented contact databases\
Inconsistent membership records\
Unreliable payment data

A well-designed rectification platform could serve a large market of
membership-driven organizations.

------------------------------------------------------------------------

# End of Document

-- Delphi Member OS
-- PostgreSQL Schema
-- Version 1.0

CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE organizations (
    organization_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    website TEXT,
    domain TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE persons (
    person_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    first_name TEXT,
    last_name TEXT,
    full_name TEXT NOT NULL,
    primary_email TEXT,
    secondary_emails JSONB NOT NULL DEFAULT '[]'::jsonb,
    primary_phone TEXT,
    secondary_phones JSONB NOT NULL DEFAULT '[]'::jsonb,
    company TEXT,
    job_title TEXT,
    location TEXT,
    linkedin_url TEXT,
    website TEXT,
    notes TEXT,
    source_confidence_score NUMERIC(5,2),
    last_verified_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_persons_primary_email ON persons (LOWER(primary_email));
CREATE INDEX idx_persons_full_name_trgm ON persons USING gin (full_name gin_trgm_ops);

CREATE TABLE person_organizations (
    person_organization_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    person_id UUID NOT NULL REFERENCES persons(person_id) ON DELETE CASCADE,
    organization_id UUID NOT NULL REFERENCES organizations(organization_id) ON DELETE CASCADE,
    relationship_type TEXT NOT NULL DEFAULT 'member',
    is_primary BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE external_profiles (
    external_profile_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    person_id UUID REFERENCES persons(person_id) ON DELETE SET NULL,
    source_system TEXT NOT NULL CHECK (source_system IN ('stripe','luma','mailchimp','google_sheets','apple_contacts','manual_csv','other')),
    source_record_id TEXT NOT NULL,
    source_payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    source_hash TEXT,
    source_last_seen_at TIMESTAMPTZ,
    last_synced_at TIMESTAMPTZ,
    sync_status TEXT NOT NULL DEFAULT 'pending' CHECK (sync_status IN ('pending','synced','error','ignored')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (source_system, source_record_id)
);

CREATE INDEX idx_external_profiles_person_id ON external_profiles (person_id);
CREATE INDEX idx_external_profiles_source ON external_profiles (source_system, source_record_id);

CREATE TABLE canonical_membership_tiers (
    canonical_tier_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    canonical_tier_name TEXT NOT NULL UNIQUE,
    tier_family TEXT NOT NULL,
    description TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE tier_price_schedules (
    tier_price_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    canonical_tier_id UUID NOT NULL REFERENCES canonical_membership_tiers(canonical_tier_id) ON DELETE CASCADE,
    list_price NUMERIC(12,2) NOT NULL,
    currency TEXT NOT NULL DEFAULT 'JPY',
    billing_frequency TEXT NOT NULL CHECK (billing_frequency IN ('monthly','quarterly','annual','one_time','custom')),
    effective_from DATE NOT NULL,
    effective_to DATE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE membership_alias_mappings (
    alias_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_system TEXT NOT NULL CHECK (source_system IN ('stripe','luma','mailchimp','google_sheets','apple_contacts','manual_csv','other')),
    source_tier_name TEXT,
    source_product_id TEXT,
    source_plan_id TEXT,
    source_price NUMERIC(12,2),
    currency TEXT DEFAULT 'JPY',
    canonical_tier_id UUID NOT NULL REFERENCES canonical_membership_tiers(canonical_tier_id) ON DELETE CASCADE,
    confidence_score NUMERIC(5,2) NOT NULL DEFAULT 0,
    effective_from DATE,
    effective_to DATE,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_membership_alias_mappings_lookup
ON membership_alias_mappings (source_system, source_tier_name, source_product_id, source_plan_id);

CREATE TABLE memberships (
    membership_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    person_id UUID NOT NULL REFERENCES persons(person_id) ON DELETE CASCADE,
    organization_id UUID REFERENCES organizations(organization_id) ON DELETE SET NULL,
    canonical_tier_id UUID NOT NULL REFERENCES canonical_membership_tiers(canonical_tier_id) ON DELETE RESTRICT,
    membership_relationship_type TEXT NOT NULL DEFAULT 'individual'
        CHECK (membership_relationship_type IN ('individual','corporate_seat','complimentary','partner','sponsor','internal','staff')),
    status TEXT NOT NULL DEFAULT 'unknown'
        CHECK (status IN ('active','inactive','past_due','complimentary','manual','suspended','unknown')),
    payment_method_type TEXT NOT NULL DEFAULT 'manual_override'
        CHECK (payment_method_type IN ('stripe_auto','bank_transfer','cash','manual_override','comped','unknown')),
    price_paid NUMERIC(12,2),
    price_currency TEXT NOT NULL DEFAULT 'JPY',
    discount_percent NUMERIC(5,2),
    discount_reason TEXT,
    list_price_snapshot NUMERIC(12,2),
    billing_frequency TEXT CHECK (billing_frequency IN ('monthly','quarterly','annual','one_time','custom')),
    start_date DATE,
    end_date DATE,
    renewal_date DATE,
    last_payment_date DATE,
    amount_last_paid NUMERIC(12,2),
    source_of_truth TEXT,
    relationship_strength TEXT
        CHECK (relationship_strength IN ('core','active','peripheral','dormant','prospect')),
    review_required BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_memberships_person_id ON memberships (person_id);
CREATE INDEX idx_memberships_status ON memberships (status);

CREATE TABLE membership_seats (
    membership_seat_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    membership_id UUID NOT NULL REFERENCES memberships(membership_id) ON DELETE CASCADE,
    membership_holder_person_id UUID REFERENCES persons(person_id) ON DELETE SET NULL,
    seat_holder_person_id UUID REFERENCES persons(person_id) ON DELETE SET NULL,
    seat_title TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE merge_candidates (
    merge_candidate_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    left_person_id UUID NOT NULL REFERENCES persons(person_id) ON DELETE CASCADE,
    right_person_id UUID NOT NULL REFERENCES persons(person_id) ON DELETE CASCADE,
    confidence_score NUMERIC(5,2) NOT NULL,
    strong_signal_count INTEGER NOT NULL DEFAULT 0,
    medium_signal_count INTEGER NOT NULL DEFAULT 0,
    weak_signal_count INTEGER NOT NULL DEFAULT 0,
    explanation JSONB NOT NULL DEFAULT '[]'::jsonb,
    recommended_action TEXT NOT NULL DEFAULT 'review'
        CHECK (recommended_action IN ('auto_merge','review','ignore')),
    status TEXT NOT NULL DEFAULT 'open'
        CHECK (status IN ('open','approved','rejected','merged','ignored')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMPTZ
);

CREATE TABLE review_queue_items (
    review_item_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    item_type TEXT NOT NULL
        CHECK (item_type IN ('duplicate_contact','unknown_tier','conflicting_membership','missing_email','multiple_stripe_customers','price_anomaly','sync_error')),
    related_person_id UUID REFERENCES persons(person_id) ON DELETE SET NULL,
    related_membership_id UUID REFERENCES memberships(membership_id) ON DELETE SET NULL,
    related_external_profile_id UUID REFERENCES external_profiles(external_profile_id) ON DELETE SET NULL,
    severity TEXT NOT NULL DEFAULT 'medium'
        CHECK (severity IN ('low','medium','high','critical')),
    title TEXT NOT NULL,
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    status TEXT NOT NULL DEFAULT 'open'
        CHECK (status IN ('open','in_progress','resolved','dismissed')),
    assigned_to TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMPTZ
);

CREATE TABLE sync_runs (
    sync_run_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_system TEXT NOT NULL,
    direction TEXT NOT NULL CHECK (direction IN ('inbound','outbound')),
    status TEXT NOT NULL CHECK (status IN ('started','completed','failed')),
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    records_processed INTEGER NOT NULL DEFAULT 0,
    records_failed INTEGER NOT NULL DEFAULT 0,
    error_summary TEXT
);

CREATE TABLE sync_events (
    sync_event_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sync_run_id UUID REFERENCES sync_runs(sync_run_id) ON DELETE SET NULL,
    source_system TEXT NOT NULL,
    related_person_id UUID REFERENCES persons(person_id) ON DELETE SET NULL,
    related_membership_id UUID REFERENCES memberships(membership_id) ON DELETE SET NULL,
    action_type TEXT NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    status TEXT NOT NULL CHECK (status IN ('success','error')),
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE merge_audit_logs (
    decision_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    decision_type TEXT NOT NULL
        CHECK (decision_type IN ('auto_merge','manual_merge','split','tier_remap','field_override')),
    performed_by TEXT,
    reason TEXT,
    before_json JSONB NOT NULL,
    after_json JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE field_source_priorities (
    field_source_priority_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    field_name TEXT NOT NULL,
    source_system TEXT NOT NULL,
    priority_rank INTEGER NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (field_name, source_system),
    UNIQUE (field_name, priority_rank)
);

INSERT INTO canonical_membership_tiers (canonical_tier_name, tier_family, description) VALUES
('Core Member', 'Paid Individual', 'Standard paid individual membership'),
('Corporate Member', 'Paid Corporate', 'Corporate membership with possible seats'),
('Complimentary', 'Complimentary', 'No-cost membership'),
('Prospect', 'Pipeline', 'Not yet a member'),
('Partner', 'Special', 'Partner or sponsored relationship');

INSERT INTO field_source_priorities (field_name, source_system, priority_rank) VALUES
('email', 'stripe', 1),
('email', 'mailchimp', 2),
('email', 'luma', 3),
('email', 'google_sheets', 4),
('email', 'apple_contacts', 5),
('phone', 'apple_contacts', 1),
('phone', 'google_sheets', 2),
('phone', 'stripe', 3),
('name', 'stripe', 1),
('name', 'luma', 2),
('name', 'mailchimp', 3),
('company', 'apple_contacts', 1),
('company', 'google_sheets', 2),
('membership_status', 'stripe', 1),
('membership_status', 'google_sheets', 2),
('membership_status', 'mailchimp', 3);

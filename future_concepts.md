# Future Concepts

This document captures product directions that are important, but not required for the first implementation pass of Member OS.

The goal is to preserve the larger product vision while keeping the current build focused on the canonical data foundation, identity resolution, and source synchronization.

## 1. Members vs Contacts

Member OS should eventually support two related but distinct concepts:

- `members`: people with an active or historical relationship to the network through a membership construct
- `contacts`: people known to the network operator, staff, or managers, even if they are not members

This matters because a network's value is not only in its paying members. It also includes:

- advisors
- operators
- investors
- potential speakers
- referral targets
- strategic partners
- people a manager knows personally

Not every useful person in the network should be forced into a membership record.

## 2. Dual Dashboard Model

A later version of the platform should support at least two operational lenses:

### All Contacts Dashboard

A broader view of the full relationship universe, including:

- members
- former members
- prospects
- personal contacts
- strategic contacts
- unclassified people

This dashboard would help managers understand the full network surface area they can draw from.

### Member Sub-Dashboard

A narrower operational view focused on active and relevant network members, including:

- membership tier
- payment status
- engagement
- review flags
- segmentation
- introduction opportunities

This lets staff work operationally with the formal network while still benefiting from the larger contact graph behind it.

## 3. Introduction Recommendation Layer

One of the highest-value future services inside Member OS could be an introduction recommendation system.

The product goal would be:

- recommend who a member should meet
- recommend who can help a member advance their mission
- recommend who is aligned by industry, role, geography, or strategic need
- surface why the recommendation exists

Possible matching inputs:

- industry
- job title
- organization
- location
- expertise
- interests
- relationship strength
- membership tier
- historical event attendance
- shared connections
- manually curated notes

Possible outputs:

- recommended introductions for a member
- ranked connection opportunities
- "people you should know" lists
- operator-facing prompts for warm intros

## 4. Matching Has Two Different Meanings

Member OS should distinguish between two different matching systems:

### Identity Matching

This is the current core problem:

- determining whether multiple records refer to the same person
- resolving duplicates
- normalizing aliases, phone-only records, and fragmented source data

### Relationship Matching

This is a later product capability:

- identifying who should be introduced to whom
- finding aligned contacts for a member's goals
- recommending strategic connections across the network

These are related, but they are not the same feature.

## 5. Likely Future Data Model Extensions

When this concept is developed, the schema will likely need additional structures such as:

- richer person attributes for expertise, interests, and goals
- tags or taxonomy tables
- relationship or connection tables between people
- introduction recommendation tables
- introduction outcome tracking
- manager-owned contact lists or portfolio views
- visibility/privacy controls for who can see which contacts

The important architectural principle is:

`person` should remain the universal entity, while `membership` is only one layer of relationship on top of that person.

## 6. Suggested Phasing

This idea is best treated as a later build after the core source-of-truth system is stable.

### Phase 1

- canonical person and membership data model
- ingestion and normalization
- identity resolution
- review workflows
- outbound sync

### Phase 2

- broader contact graph beyond members
- all-contacts dashboard plus member sub-dashboard
- manager-specific views into their networks

### Phase 3

- introduction recommendation engine
- matching logic for strategic intros
- explainable recommendation workflows
- performance tracking on introductions and outcomes

## 7. Product Value

If implemented well, this would make Member OS more than a data cleanup tool.

It would become:

- a system of record
- a network intelligence platform
- an operator workflow tool
- a high-value recommendation engine for relationship-driven organizations


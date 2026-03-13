# Member OS
## UI Wireframes and Dashboard Layout

## 1. Design Intent

The UI should feel operational, not decorative. The purpose is to help a small team quickly:
- identify broken records
- merge duplicates safely
- understand membership status
- map chaotic tier names
- push clean data back into the tools they actually use

The interface should be clean, dense, and practical.

---

## 2. Primary Navigation

Recommended left-hand navigation:

1. Dashboard
2. Members
3. Memberships
4. Duplicate Review
5. Tier Mapping
6. Review Queue
7. Sync Monitor
8. Imports / Exports
9. Settings

---

## 3. Dashboard

### Purpose
Give the operator a high-level operational picture within a few seconds.

### Layout

Top KPI row:
- Total Canonical Members
- Active Memberships
- Open Duplicate Reviews
- Unknown Tiers
- Sync Errors
- Discounted Members

Middle row:
- Recent Sync Activity panel
- Review Queue by severity
- Memberships by canonical tier

Bottom row:
- Recent changes log
- Price anomaly alerts
- Newly detected source records

### Wireframe

```text
+---------------------------------------------------------------+
| Dashboard                                                     |
+---------------------------------------------------------------+
| Total Members | Active Members | Duplicate Reviews | Errors   |
| 1,248         | 332            | 48                | 6        |
+---------------------------------------------------------------+
| Recent Sync Activity     | Review Queue        | Tier Mix     |
| Stripe inbound OK        | High: 5             | Core: 180    |
| Mailchimp outbound fail  | Medium: 17          | Corp: 52     |
| Luma inbound OK          | Low: 26             | Comp: 24     |
+---------------------------------------------------------------+
| Recent Changes           | Price Anomalies     | New Records  |
+---------------------------------------------------------------+
```

---

## 4. Members Page

### Purpose
Browse, search, and inspect canonical people.

### Table columns
- Name
- Primary Email
- Company
- Canonical Tier
- Membership Status
- Payment Method
- Last Seen
- Review Flags

### Filters
- search
- tier
- status
- company
- source system
- review required only

### Detail Drawer / Page Sections
- profile
- memberships
- external profiles
- notes
- audit history
- review items

### Wireframe

```text
+----------------------------------------------------------------------------------+
| Members                                                                          |
+----------------------------------------------------------------------------------+
| Search [_______________]  Tier [All]  Status [All]  Review Only [ ]             |
+----------------------------------------------------------------------------------+
| Name         | Email              | Company       | Tier         | Flags         |
| Jane Smith   | jane@alpha.com     | Alpha Capital | Core Member  | duplicate     |
| Matt Ketchum | matt@mkultraman... | Akiyaz        | Partner      | none          |
+----------------------------------------------------------------------------------+
| [Click row opens full member detail]                                             |
+----------------------------------------------------------------------------------+
```

---

## 5. Member Detail Page

### Sections
1. Header card
2. Canonical profile fields
3. Membership cards
4. External profile records
5. Merge history
6. Manual notes
7. Actions

### Actions
- Edit person
- Merge into another person
- Split record
- Create membership
- Push update to downstream systems

### Wireframe

```text
+---------------------------------------------------------------+
| Jane Smith                                                    |
| jane@alpha.com | Alpha Capital | Active Core Member           |
+---------------------------------------------------------------+
| Profile                    | Membership                       |
| Name, phones, links        | Tier: Core Member                |
| Company, title             | Price Paid: ¥150,000             |
| Notes                      | Discount: 40%                    |
+---------------------------------------------------------------+
| External Profiles                                              |
| Stripe | Mailchimp | Luma | Sheets                            |
+---------------------------------------------------------------+
| Audit History                                                 |
+---------------------------------------------------------------+
```

---

## 6. Duplicate Review Page

### Purpose
Resolve likely duplicate contacts.

### Table columns
- Left person
- Right person
- Confidence score
- Strong signals
- Recommended action
- Status

### Candidate Detail Panel
Show side-by-side comparison:
- names
- emails
- phones
- company
- memberships
- source records

### Primary buttons
- Approve Merge
- Reject
- Ignore
- Open both records

### Wireframe

```text
+----------------------------------------------------------------------------------+
| Duplicate Review                                                                 |
+----------------------------------------------------------------------------------+
| Left Person      | Right Person     | Score | Signals        | Action           |
| Jane Smith       | Jane A. Smith    | 97    | email, company | auto_merge       |
| John Doe         | Jonathan Doe     | 82    | name, domain   | review           |
+----------------------------------------------------------------------------------+

Selected Candidate:
+-----------------------------------+---------------------------------------------+
| Left Record                       | Right Record                                |
| Jane Smith                        | Jane A. Smith                               |
| jane@alpha.com                    | jane@alpha.com                              |
| Alpha Capital                     | Alpha Capital                               |
+-----------------------------------+---------------------------------------------+
| [Approve Merge] [Reject] [Ignore]                                               |
+----------------------------------------------------------------------------------+
```

---

## 7. Memberships Page

### Purpose
Inspect memberships independently from people.

### Table columns
- Person
- Organization
- Canonical Tier
- Status
- Payment Method
- Price Paid
- List Price
- Discount
- Renewal Date
- Review Flag

### Useful filters
- tier
- active only
- discounted only
- manual payers only
- corporate seats
- anomalies only

---

## 8. Tier Mapping Page

### Purpose
Resolve source-specific membership naming chaos.

### Split layout
Left side:
- incoming unknown tier names
- source system
- source price
- count of affected records

Right side:
- canonical tiers
- create new canonical tier
- map alias
- map with effective dates

### Wireframe

```text
+----------------------------------------------------------------------------------+
| Tier Mapping                                                                     |
+----------------------------------------------------------------------------------+
| Unknown Source Tier         | Source     | Price      | Records                  |
| Founding Circle             | Stripe     | 250000     | 24                       |
| Executive Partner           | Sheets     | 150000     | 8                        |
+----------------------------------------------------------------------------------+
| Map To Canonical Tier: [Core Member v]   [Save Mapping]                          |
+----------------------------------------------------------------------------------+
```

---

## 9. Review Queue

### Purpose
Central place for all unresolved operational issues, not only duplicates.

### Item types
- duplicate contact
- unknown tier
- conflicting membership
- missing email
- multiple Stripe customers
- price anomaly
- sync error

### Columns
- Severity
- Type
- Title
- Related Person
- Assigned To
- Status
- Created At

### Detail view
- issue summary
- related records
- recommended next step
- resolution note box

---

## 10. Sync Monitor

### Purpose
Track system integration health.

### Panels
- connector status cards
- recent sync runs
- failed sync events
- stale source warnings

### Connector card contents
- source system
- last inbound sync
- last outbound sync
- status badge
- recent error count
- test connection button

### Wireframe

```text
+----------------------------------------------------------------------------------+
| Sync Monitor                                                                     |
+----------------------------------------------------------------------------------+
| Stripe      | Last inbound: 10m ago | Status: OK     | Errors: 0                |
| Mailchimp   | Last outbound: 2h ago | Status: Error  | Errors: 4                |
| Luma        | Last inbound: 1h ago  | Status: OK     | Errors: 0                |
+----------------------------------------------------------------------------------+
| Recent Sync Runs                                                                 |
+----------------------------------------------------------------------------------+
| Failed Events                                                                    |
+----------------------------------------------------------------------------------+
```

---

## 11. Imports / Exports

### Purpose
Handle CSV-based imports and operational exports.

### Sections
- upload CSV
- import history
- export canonical persons
- export memberships
- export unresolved review queue

### Upload flow
1. Select file
2. Choose source type
3. Preview parsed columns
4. Confirm import
5. Review import summary

---

## 12. Settings

### Sections
- connector credentials
- user roles
- field source priorities
- confidence thresholds
- sync rules
- discount anomaly thresholds

### Examples
- auto-merge threshold: 95
- review threshold: 75
- price anomaly: below 30 percent of current list price
- write-back enabled: Mailchimp only

---

## 13. UX Recommendations

### Dense tables, fast filtering
This product is for operators doing cleanup work. Prioritize:
- keyboard-friendly filtering
- sortable tables
- bulk actions where safe
- quick navigation between related records

### Human-readable explanations
When the system recommends a merge, explain why:
- same email
- same company
- matching phone
- overlapping event history

### Soft warnings before destructive actions
Before merge, split, or outbound overwrite:
- show the affected systems
- show the changed fields
- require confirmation

### Audit visibility
Users should always be able to see:
- who changed something
- when it changed
- what it was before

---

## 14. Suggested MVP UI Build Order

1. Dashboard
2. Members table
3. Member detail page
4. Duplicate review interface
5. Tier mapping page
6. Review queue
7. Sync monitor
8. Imports / exports
9. Settings

# Docs Index

This file is the entry point for the written reference material in this repository.

## Recommended Reading Order

1. `README.md`
2. `member_os_project_spec.md`
3. `system_architecture.md`
4. `api_spec.md`
5. `ui_wireframes.md`
6. `schema_deviations.md`
7. `future_concepts.md`

## Reference Map

### Product and Scope

- `README.md`: project bootstrap, local setup, and quick links
- `member_os_project_spec.md`: high-level product and technical specification
- `future_concepts.md`: later-phase ideas that are intentionally out of current build scope

### Architecture and Data Model

- `system_architecture.md`: service boundaries, data flow, and long-term platform direction
- `database_schema.sql`: original SQL-first schema draft
- `schema_deviations.md`: intentional differences between the original SQL draft and the Django/PostgreSQL implementation

### API and UI

- `api_spec.md`: current and planned API surface
- `ui_wireframes.md`: dashboard and workflow concepts for operators

## Current Implementation Anchors

- Django settings and bootstrap: `member_os/settings/`
- Core domain models: `core/models.py`
- Initial schema migrations: `core/migrations/`
- CSV/manual import pipeline: `core/imports.py`
- API views and routes: `core/views.py`, `core/urls.py`
- Tests: `core/tests.py`

## Notes

- The docs are written to describe the product generically, not a specific pilot organization.
- Some examples use placeholder tiers or sample names to explain workflows without embedding client-specific branding.

# Member OS

Canonical contact and membership system for cleaning, normalizing, and synchronizing member data across fragmented platforms.

## Bootstrap Stack

- Django 5
- PostgreSQL 16
- Docker Compose for local database setup
- Environment-specific settings modules for development, staging, and production

This repository starts with a Django-first bootstrap because the product is operationally heavy and needs admin workflows quickly.

## Quick Start

1. Create and activate a virtualenv:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Copy the environment template:

   ```bash
   cp .env.example .env
   ```

4. Start PostgreSQL:

   ```bash
   docker compose up -d postgres
   ```

5. Apply migrations:

   ```bash
   python manage.py migrate
   ```

6. Create an admin user:

   ```bash
   python manage.py createsuperuser
   ```

7. Run the development server:

   ```bash
   python manage.py runserver
   ```

8. Sign in through the operator shell:

   - staff login: `http://127.0.0.1:8000/login/`
   - operator home: `http://127.0.0.1:8000/home/`
   - Django admin: `http://127.0.0.1:8000/admin/`

9. Run imports from the browser:

   - open `http://127.0.0.1:8000/home/`
   - upload a CSV and choose the source system
   - inspect per-run failures directly on the page

10. Use the operator pages:

   - people directory: `http://127.0.0.1:8000/people/`
   - sample CSV template: `http://127.0.0.1:8000/imports/sample.csv`
   - review queue: `http://127.0.0.1:8000/reviews/`

11. Apple Contacts workflow:

   ```bash
   ./scripts/apple_contacts_to_member_os.sh --output ./tmp/apple-contacts.csv
   ./scripts/apple_contacts_to_member_os.sh --import --output ./tmp/apple-contacts.csv
   ```

   Notes:

   - the first run will prompt macOS to grant Contacts access to Terminal or `osascript`
   - export writes a CSV in the Member OS import shape
   - `--import` runs the standard Django ingestion pipeline with `source_system=apple_contacts`

12. Stripe workflow:

   ```bash
   export STRIPE_API_KEY=sk_live_or_test_...
   ./scripts/stripe_to_member_os.sh --output ./tmp/stripe-customers.csv
   ./scripts/stripe_to_member_os.sh --import --output ./tmp/stripe-customers.csv
   ```

   Notes:

   - export calls Stripe's official REST API directly using your secret key
   - it fetches customers plus subscriptions, then writes a Member OS CSV
   - `--import` runs the standard Django ingestion pipeline with `source_system=stripe`
   - the Django web server does not need to be running for the CLI export/import flow

## Deploy On Railway

This repo includes a root-level Railway config in `railway.toml` for the Django app.

What it does:

- builds with Railpack
- runs `collectstatic` during the build
- runs `migrate` before each deploy
- starts Gunicorn on Railway's injected `PORT`
- uses `/api/v1/health` as the healthcheck path

Required Railway variables for the app service:

- `DJANGO_SECRET_KEY`
- `DJANGO_SETTINGS_MODULE=member_os.settings.production`
- `PGDATABASE=${{Postgres.PGDATABASE}}`
- `PGUSER=${{Postgres.PGUSER}}`
- `PGPASSWORD=${{Postgres.PGPASSWORD}}`
- `PGHOST=${{Postgres.PGHOST}}`
- `PGPORT=${{Postgres.PGPORT}}`

Optional but recommended:

- `DJANGO_ALLOWED_HOSTS` for any custom domains
- `DJANGO_CSRF_TRUSTED_ORIGINS` for any custom domains

Notes:

- The app auto-adds `RAILWAY_PUBLIC_DOMAIN` to `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` when Railway provides it.
- `DJANGO_SETTINGS_MODULE` should be set on the Railway service itself so the same value is available during build, pre-deploy, and runtime.
- `railway.toml` uses the virtualenv binaries explicitly during pre-deploy and runtime to avoid PATH differences between Railway build and deploy phases.
- The archived FastAPI scaffold at `archive/backend-fastapi-legacy/` is not used by this Railway config. It targets the Django app at the repository root.

## Useful Endpoints

- Health check: `GET /api/v1/health`
- CSV import: `POST /api/v1/external-profiles/import/csv`
- Import run detail: `GET /api/v1/import-runs/{import_run_id}`
- Staff login: `/login/`
- Operator home: `/home/`
- People directory: `/people/`
- Review queue: `/reviews/`
- Sample import template: `/imports/sample.csv`
- Admin: `/admin/`

Example CSV import:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/external-profiles/import/csv \
  -F "source_system=manual_csv" \
  -F "file=@contacts.csv"
```

## Settings Modules

- Development: `member_os.settings.development`
- Staging: `member_os.settings.staging`
- Production: `member_os.settings.production`

Set `DJANGO_SETTINGS_MODULE` if you need to override the default module used by `manage.py`.

## Repository Layout

- active Django app: repository root
- archived FastAPI scaffold: `archive/backend-fastapi-legacy/`

## Documentation

- Product spec: `member_os_project_spec.md`
- System architecture: `system_architecture.md`
- API reference: `api_spec.md`
- UI wireframes: `ui_wireframes.md`
- Schema notes: `schema_deviations.md`
- Future roadmap ideas: `future_concepts.md`
- Full docs index: `docs_index.md`

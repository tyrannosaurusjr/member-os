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
- `railway.toml` forces `member_os.settings.production` for build, migrate, and start commands, so you do not need to set `DJANGO_SETTINGS_MODULE` manually on Railway.
- The legacy `backend/` directory is not used by this Railway config. It targets the Django app at the repository root.

## Useful Endpoints

- Health check: `GET /api/v1/health`
- CSV import: `POST /api/v1/external-profiles/import/csv`
- Import run detail: `GET /api/v1/import-runs/{import_run_id}`
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

## Documentation

- Product spec: `member_os_project_spec.md`
- System architecture: `system_architecture.md`
- API reference: `api_spec.md`
- UI wireframes: `ui_wireframes.md`
- Schema notes: `schema_deviations.md`
- Future roadmap ideas: `future_concepts.md`
- Full docs index: `docs_index.md`

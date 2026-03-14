import os
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / '.env')


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {'1', 'true', 't', 'yes', 'y', 'on'}


def env_list(name: str, default: list[str] | None = None) -> list[str]:
    value = os.getenv(name)
    if not value:
        return default or []
    return [item.strip() for item in value.split(',') if item.strip()]


def env_first(*names: str, default: str | None = None) -> str | None:
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return default


def append_unique(values: list[str], value: str | None):
    if value and value not in values:
        values.append(value)


def normalize_host(value: str | None) -> str | None:
    if not value:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    if '://' in normalized:
        parsed = urlparse(normalized)
        normalized = parsed.netloc or parsed.path
    normalized = normalized.split('/', 1)[0]
    return normalized.split(':', 1)[0].strip() or None


def normalize_origin(value: str | None) -> str | None:
    if not value:
        return None
    normalized = value.strip().rstrip('/')
    if not normalized:
        return None
    if '://' in normalized:
        parsed = urlparse(normalized)
        if parsed.scheme and parsed.netloc:
            return f'{parsed.scheme}://{parsed.netloc}'
        return None

    host = normalize_host(normalized)
    if not host:
        return None
    return f'https://{host}'


SECRET_KEY = os.getenv(
    'DJANGO_SECRET_KEY', 'django-insecure-dev-secret-key-change-me'
)
DEBUG = env_bool('DJANGO_DEBUG', False)
ALLOWED_HOSTS = env_list('DJANGO_ALLOWED_HOSTS', ['127.0.0.1', 'localhost'])
append_unique(ALLOWED_HOSTS, normalize_host(os.getenv('RAILWAY_PUBLIC_DOMAIN')))
append_unique(ALLOWED_HOSTS, normalize_host(os.getenv('RAILWAY_PRIVATE_DOMAIN')))

CSRF_TRUSTED_ORIGINS = env_list('DJANGO_CSRF_TRUSTED_ORIGINS', [])
append_unique(
    CSRF_TRUSTED_ORIGINS,
    normalize_origin(os.getenv('RAILWAY_PUBLIC_DOMAIN')),
)

INSTALLED_APPS = [
    'django.contrib.postgres',
    'whitenoise.runserver_nostatic',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'core',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'member_os.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'member_os.wsgi.application'
ASGI_APPLICATION = 'member_os.asgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': env_first('POSTGRES_DB', 'PGDATABASE', default='member_os'),
        'USER': env_first('POSTGRES_USER', 'PGUSER', default='member_os'),
        'PASSWORD': env_first(
            'POSTGRES_PASSWORD',
            'PGPASSWORD',
            default='member_os',
        ),
        'HOST': env_first('POSTGRES_HOST', 'PGHOST', default='127.0.0.1'),
        'PORT': env_first('POSTGRES_PORT', 'PGPORT', default='5432'),
        'CONN_MAX_AGE': int(os.getenv('POSTGRES_CONN_MAX_AGE', '60')),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STORAGES = {
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

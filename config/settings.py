import os
import secrets
import sys
from pathlib import Path

from dotenv import load_dotenv
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')


def _env_bool(key: str, default: bool = False) -> bool:
    val = os.getenv(key)
    if val is None:
        return default
    return val.strip().lower() in ('1', 'true', 'yes', 'on')


def _env_list(key: str, default=None):
    val = os.getenv(key)
    if val is None or not val.strip():
        return default if default is not None else []
    return [x.strip() for x in val.split(',') if x.strip()]


_railway_prod = os.getenv('RAILWAY_ENVIRONMENT') == 'production'
_collectstatic = len(sys.argv) > 1 and sys.argv[1] == 'collectstatic'

_secret_env = (os.getenv('SECRET_KEY') or os.getenv('DJANGO_SECRET_KEY') or '').strip()
DEBUG = _env_bool('DEBUG', False if _railway_prod else True)

if _secret_env:
    SECRET_KEY = _secret_env
elif _collectstatic:
    SECRET_KEY = (os.getenv('SECRET_KEY_BUILD') or '').strip() or (
        'railway-build-collectstatic-' + secrets.token_urlsafe(48)
    )
elif DEBUG:
    SECRET_KEY = 'django-insecure-ms-dev-key-change-in-production-!@#$%'
else:
    raise ImproperlyConfigured(
        'Укажите переменную окружения SECRET_KEY (для Railway: Variables → New Variable). '
        'Сгенерируйте ключ локально: '
        'python -c "from django.core.management.utils import get_random_secret_key; '
        'print(get_random_secret_key())"'
    )

_hosts = _env_list('ALLOWED_HOSTS')
if _hosts:
    ALLOWED_HOSTS = _hosts
elif DEBUG:
    ALLOWED_HOSTS = ['*']
else:
    ALLOWED_HOSTS = ['localhost', '127.0.0.1']

_csrf = _env_list('CSRF_TRUSTED_ORIGINS')
if _csrf:
    CSRF_TRUSTED_ORIGINS = _csrf

SITE_ID = int(os.getenv('SITE_ID', '1'))

LANGUAGE_CODE = os.getenv('LANGUAGE_CODE', 'ru')
TIME_ZONE = os.getenv('TIME_ZONE', 'UTC')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',

    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',

    'accounts',
    'profiles',
    'game',
    'membership',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'allauth.account.middleware.AccountMiddleware',
    'profiles.middleware.UserLanguageMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.template.context_processors.i18n',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'profiles.context_processors.user_profile',
                'accounts.context_processors.google_oauth',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

_database_url = os.getenv('DATABASE_URL', '').strip()

if not _database_url:
    # Типичный шаблон (Railway/Compose): DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT
    _db_name = (os.getenv('DB_NAME') or '').strip()
    _db_user = (os.getenv('DB_USER') or '').strip()
    _db_host = (os.getenv('DB_HOST') or '').strip()
    if _db_name and _db_user and _db_host:
        from urllib.parse import quote_plus

        _db_pass = os.getenv('DB_PASSWORD') or ''
        _db_port = (os.getenv('DB_PORT') or '5432').strip()
        _database_url = (
            f'postgresql://{quote_plus(_db_user)}:{quote_plus(_db_pass)}'
            f'@{_db_host}:{_db_port}/{_db_name}'
        )

if _database_url:
    import dj_database_url

    DATABASES = {
        'default': dj_database_url.parse(
            _database_url,
            conn_max_age=600,
            conn_health_checks=True,
            ssl_require=_env_bool('DATABASE_SSL_REQUIRE', not DEBUG),
        )
    }
elif _env_bool('USE_POSTGRES', False):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('POSTGRES_DB', 'minesweeper'),
            'USER': os.getenv('POSTGRES_USER', 'minesweeper'),
            'PASSWORD': os.getenv('POSTGRES_PASSWORD', ''),
            'HOST': os.getenv('POSTGRES_HOST', 'localhost'),
            'PORT': os.getenv('POSTGRES_PORT', '5432'),
        }
    }
else:
    _sqlite = Path(os.getenv('SQLITE_PATH', 'db.sqlite3'))
    if not _sqlite.is_absolute():
        _sqlite = BASE_DIR / _sqlite
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': _sqlite,
        }
    }

# Второй источник только для разовой команды переноса: sqlite_to_postgres
_sqlite_copy_src = os.getenv('COPY_FROM_SQLITE_PATH', '').strip()
if (
    _sqlite_copy_src
    and DATABASES['default']['ENGINE'] == 'django.db.backends.postgresql'
):
    _sp = Path(_sqlite_copy_src)
    if not _sp.is_absolute():
        _sp = BASE_DIR / _sp
    DATABASES['sqlite_legacy'] = {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': str(_sp.resolve()),
    }

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

ACCOUNT_LOGIN_METHODS = {'username', 'email'}
ACCOUNT_SIGNUP_FIELDS = ['email*', 'username*', 'password1*', 'password2*']
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_EMAIL_VERIFICATION = 'none'
ACCOUNT_DEFAULT_HTTP_PROTOCOL = 'https' if not DEBUG else 'http'

SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_LOGIN_ON_GET = True
SOCIALACCOUNT_EMAIL_REQUIRED = True
SOCIALACCOUNT_ADAPTER = 'accounts.adapters.SocialAccountAdapter'

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'

GOOGLE_OAUTH_CLIENT_ID = os.getenv('GOOGLE_OAUTH_CLIENT_ID', '')
GOOGLE_OAUTH_SECRET = os.getenv('GOOGLE_OAUTH_SECRET', '')

STRIPE_PUBLIC_KEY = os.getenv('STRIPE_PUBLIC_KEY', '').strip()
STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY', '').strip()
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET', '').strip()
# Совместимость: STRIPE_PRICE_PRO = месячный price, если не задан STRIPE_PRICE_PRO_MONTHLY
STRIPE_PRICE_PRO = os.getenv('STRIPE_PRICE_PRO', '').strip()
STRIPE_PRICE_PRO_MONTHLY = (
    os.getenv('STRIPE_PRICE_PRO_MONTHLY', '').strip() or STRIPE_PRICE_PRO
)
STRIPE_PRICE_PRO_YEARLY = os.getenv('STRIPE_PRICE_PRO_YEARLY', '').strip()
PRO_TEST_BUTTON = _env_bool('PRO_TEST_BUTTON', DEBUG)

# Google Gemini — текст к ИИ-подсказке (координаты считаются на сервере, см. game.views)
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '').strip()
GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-2.0-flash').strip()
GEMINI_HINT_EXPLAIN = _env_bool('GEMINI_HINT_EXPLAIN', True)

SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'APP': {
            'client_id': GOOGLE_OAUTH_CLIENT_ID,
            'secret': GOOGLE_OAUTH_SECRET,
        },
        'SCOPE': ['profile', 'email'],
        'AUTH_PARAMS': {'access_type': 'online'},
    }
}

USE_I18N = True
USE_L10N = True
USE_TZ = True

LANGUAGES = [
    ('ru', 'Русский'),
    ('en', 'English'),
    ('kk', 'Қазақша'),
]

LOCALE_PATHS = [BASE_DIR / 'locale']

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage',
    },
}

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

SESSION_ENGINE = 'django.contrib.sessions.backends.db'

if not DEBUG:
    if SECRET_KEY.startswith('django-insecure') and not _collectstatic:
        raise ImproperlyConfigured(
            'В продакшене нельзя использовать dev SECRET_KEY. Задайте длинную случайную строку в SECRET_KEY.'
        )
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = _env_bool('SECURE_SSL_REDIRECT', True)

    LOGGING = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'simple': {
                'format': '[{levelname}] {name}: {message}',
                'style': '{',
            },
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'formatter': 'simple',
            },
        },
        'root': {
            'handlers': ['console'],
            'level': os.getenv('LOG_LEVEL', 'INFO'),
        },
        'loggers': {
            'django': {
                'handlers': ['console'],
                'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'),
                'propagate': False,
            },
        },
    }

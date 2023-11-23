import mimetypes
import os

from reNgine.init import first_run
from reNgine.utilities import RengineTaskFormatter

mimetypes.add_type("text/javascript", ".js", True)
mimetypes.add_type("text/css", ".css", True)

# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
#       RENGINE CONFIGURATIONS
# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

# Root env vars
RENGINE_HOME = os.environ.get('RENGINE_HOME', '/usr/src/app')
RENGINE_RESULTS = os.environ.get('RENGINE_RESULTS', f'{RENGINE_HOME}/scan_results')
RENGINE_CACHE_ENABLED = bool(int(os.environ.get('RENGINE_CACHE_ENABLED', '0')))
RENGINE_RECORD_ENABLED = bool(int(os.environ.get('RENGINE_RECORD_ENABLED', '1')))
RENGINE_RAISE_ON_ERROR = bool(int(os.environ.get('RENGINE_RAISE_ON_ERROR', '0')))

# Common env vars
DEBUG = bool(int(os.environ.get('DEBUG', '0')))
DOMAIN_NAME = os.environ.get('DOMAIN_NAME', 'localhost:8000')
TEMPLATE_DEBUG = bool(int(os.environ.get('TEMPLATE_DEBUG', '0')))
SECRET_FILE = os.path.join(RENGINE_HOME, 'secret')
DEFAULT_ENABLE_HTTP_CRAWL = bool(int(os.environ.get('DEFAULT_ENABLE_HTTP_CRAWL', '1')))
DEFAULT_RATE_LIMIT = int(os.environ.get('DEFAULT_RATE_LIMIT', '150')) # requests / second
DEFAULT_HTTP_TIMEOUT = int(os.environ.get('DEFAULT_HTTP_TIMEOUT', '5')) # seconds
DEFAULT_RETRIES = int(os.environ.get('DEFAULT_RETRIES', '1'))
DEFAULT_THREADS = int(os.environ.get('DEFAULT_THREADS', '30'))
DEFAULT_GET_GPT_REPORT = bool(int(os.environ.get('DEFAULT_GET_GPT_REPORT', '1')))

# Globals
ALLOWED_HOSTS = ['*']
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SECRET_KEY = first_run(SECRET_FILE, BASE_DIR)

# Databases
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('POSTGRES_DB'),
        'USER': os.environ.get('POSTGRES_USER'),
        'PASSWORD': os.environ.get('POSTGRES_PASSWORD'),
        'HOST': os.environ.get('POSTGRES_HOST'),
        'PORT': os.environ.get('POSTGRES_PORT'),
        # 'OPTIONS':{
        #     'sslmode':'verify-full',
        #     'sslrootcert': os.path.join(BASE_DIR, 'ca-certificate.crt')
        # }
    }
}

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'rest_framework',
    'rest_framework_datatables',
    'dashboard.apps.DashboardConfig',
    'targetApp.apps.TargetappConfig',
    'scanEngine.apps.ScanengineConfig',
    'startScan.apps.StartscanConfig',
    'recon_note.apps.ReconNoteConfig',
    'django_ace',
    'django_celery_beat',
    'mathfilters',
    'drf_yasg',
    'rolepermissions'
]
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'login_required.middleware.LoginRequiredMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [(os.path.join(BASE_DIR, 'templates'))],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'reNgine.context_processors.projects'
            ],
    },
}]
ROOT_URLCONF = 'reNgine.urls'
REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
        'rest_framework_datatables.renderers.DatatablesRenderer',
    ),
    'DEFAULT_FILTER_BACKENDS': (
        'rest_framework_datatables.filters.DatatablesFilterBackend',
    ),
    'DEFAULT_PAGINATION_CLASS':(
        'rest_framework_datatables.pagination.DatatablesPageNumberPagination'
    ),
    'PAGE_SIZE': 500,
}
WSGI_APPLICATION = 'reNgine.wsgi.application'

# Password validation
# https://docs.djangoproject.com/en/2.2/ref/settings/#auth-password-validators
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.' +
                'UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.' +
                'MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.' +
                'CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.' +
                'NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/2.2/topics/i18n/
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True

# Temporary fix for celery beat crash
# See https://github.com/yogeshojha/rengine/issues/971
DJANGO_CELERY_BEAT_TZ_AWARE = False

MEDIA_URL = '/media/'
FILE_UPLOAD_MAX_MEMORY_SIZE = 100000000
FILE_UPLOAD_PERMISSIONS = 0o644
STATIC_URL = '/staticfiles/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, "static"),
]

LOGIN_REQUIRED_IGNORE_VIEW_NAMES = [
    'login',
]

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboardIndex'
LOGOUT_REDIRECT_URL = 'login'

# Tool Location
TOOL_LOCATION = '/usr/src/app/tools/'

# Number of endpoints that have the same content_length
DELETE_DUPLICATES_THRESHOLD = 10

'''
CELERY settings
'''
CELERY_BROKER_URL = os.environ.get("CELERY_BROKER", "redis://redis:6379/0")
CELERY_RESULT_BACKEND = os.environ.get("CELERY_BROKER", "redis://redis:6379/0")
CELERY_ENABLE_UTC = False
CELERY_TIMEZONE = 'UTC'
CELERY_IGNORE_RESULTS = False
CELERY_EAGER_PROPAGATES_EXCEPTIONS = True
CELERY_TRACK_STARTED = True
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
'''
ROLES and PERMISSIONS
'''
ROLEPERMISSIONS_MODULE = 'reNgine.roles'
ROLEPERMISSIONS_REDIRECT_TO_LOGIN = True

'''
Cache settings
'''
RENGINE_TASK_IGNORE_CACHE_KWARGS = ['ctx']


DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

'''
LOGGING settings
'''
LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'handlers': {
        'null': {
            'class': 'logging.NullHandler'
        },
        'default': {
            'class': 'logging.StreamHandler',
            'formatter': 'default',
        },
        'brief': {
            'class': 'logging.StreamHandler',
            'formatter': 'brief'
        },
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'brief'
        },
        'task': {
            'class': 'logging.StreamHandler',
            'formatter': 'task'
        },
        'db': {
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'brief',
            'filename': 'db.log',
            'maxBytes': 1024,
            'backupCount': 3
        }
    },
    'formatters': {
        'default': {
            'format': '%(message)s'
        },
        'brief': {
            'format': '%(name)-10s | %(message)s'
        },
        'task': {
            '()': lambda : RengineTaskFormatter('%(task_name)-34s | %(levelname)s | %(message)s')
        }
    },
    'loggers': {
        '': {
            'handlers': ['brief'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False
        },
        'celery.app.trace': {
            'handlers': ['null'],
            'propagate': False,
        },
        'celery.task': {
            'handlers': ['task'],
            'propagate': False
        },
        'celery.worker': {
            'handlers': ['null'],
            'propagate': False,
        },
        'django.server': {
            'handlers': ['console'],
            'propagate': False
        },
        'django.db.backends': {
            'handlers': ['db'],
            'level': 'INFO',
            'propagate': False
        },
        'reNgine.tasks': {
            'handlers': ['task'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False
        }
    },
}

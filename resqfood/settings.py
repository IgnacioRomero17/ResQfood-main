
from pathlib import Path
import environ, os
BASE_DIR = Path(__file__).resolve().parent.parent

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DJANGO_DEBUG=(bool, True),
)
environ.Env.read_env(os.path.join(BASE_DIR, ".env"))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = env("DJANGO_DEBUG")

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = [
    "127.0.0.1",
    "localhost",
    "resqfood-cp13.onrender.com",
]

CSRF_TRUSTED_ORIGINS = [
    "https://resqfood-cp13.onrender.com",
    "http://127.0.0.1",
    "http://localhost",
]

# Application definition

INSTALLED_APPS = [

    "whitenoise.runserver_nostatic",
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

       #  Apps
    "core",
    "marketplace",
    "accounts",
    "packs",
    "payments",
    "usuarios",

    # Django admin
    "django.contrib.admin",


    # 3rd party
    "rest_framework",
    "django_filters",
    "corsheaders",

   
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware", 
    'django.middleware.security.SecurityMiddleware',
    "whitenoise.middleware.WhiteNoiseMiddleware",
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    
    # ...
]

ROOT_URLCONF = 'resqfood.urls'


TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        "DIRS": [BASE_DIR / "templates"], 
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'marketplace.context_processors.cart_badge',
                'core.context_processors.reminders_cp',
            ],
        },
    },
]

WSGI_APPLICATION = "resqfood.wsgi.application"
ASGI_APPLICATION = "resqfood.asgi.application"



# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

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


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'es-ar'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = "core.User"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework.authentication.SessionAuthentication",  
        "rest_framework.authentication.BasicAuthentication",
        "rest_framework_simplejwt.authentication.JWTAuthentication",  
    ),
    
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.AllowAny",
    ),
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 12,
}


# Payments feature flags / config
PAYMENTS_USE_LOCAL_MOCK = os.getenv("PAYMENTS_USE_LOCAL_MOCK", "true").lower() == "true"

# Mercado Pago configuration 
MP_ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN", "")
MP_PUBLIC_KEY = os.getenv("MP_PUBLIC_KEY", "")
MP_NOTIFICATION_URL = os.getenv("MP_NOTIFICATION_URL", "https://example.com/webhooks/mercadopago/")
MP_BACK_URL_SUCCESS = os.getenv("MP_BACK_URL_SUCCESS", "http://localhost:8000/payments/success/")
MP_BACK_URL_PENDING = os.getenv("MP_BACK_URL_PENDING", "http://localhost:8000/payments/pending/")
MP_BACK_URL_FAILURE = os.getenv("MP_BACK_URL_FAILURE", "http://localhost:8000/payments/failure/")

# Webhook verification secret (HMAC). 
MP_WEBHOOK_SECRET = os.getenv("MP_WEBHOOK_SECRET", "")

# Bank transfer info (for transfer flow)
BANK_INFO_ALIAS = os.getenv("BANK_INFO_ALIAS", "mi.empresa.alias")
BANK_INFO_CBU = os.getenv("BANK_INFO_CBU", "0000000000000000000000")
BANK_INFO_TITULAR = os.getenv("BANK_INFO_TITULAR", "Mi Empresa SA")
BANK_INFO_CUIT = os.getenv("BANK_INFO_CUIT", "30-00000000-0")

CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",    
]


LOGIN_URL = "login"                
LOGIN_REDIRECT_URL = "packs:list"  
LOGOUT_REDIRECT_URL = "home" 


EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"


# Use stock images when real image is missing
USE_STOCK_IMAGES_FOR_EMPTY = True
# Root under static/ for stock assets
STOCK_IMAGE_ROOT = "img/stock"
# NEW: force stock everywhere (ignore media files)
USE_STOCK_IMAGES_FORCE_STOCK = True


from django.contrib.messages import constants as messages
MESSAGE_TAGS = {
    messages.DEBUG: "debug",
    messages.INFO: "info",
    messages.SUCCESS: "success",
    messages.WARNING: "warning",
    messages.ERROR: "error",
}

# Settings reminders
REMINDER_ENABLED = True
REMINDER_WINDOW_MINUTES = int(os.getenv("REMINDER_WINDOW_MINUTES", "120"))
REMINDER_EMAIL_SENDER = os.getenv("REMINDER_EMAIL_SENDER", "notificaciones@resqfood.local")




USE_STOCK_IMAGES_PREFER_STOCK = True


# Static & media
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]  

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"


if DEBUG:
    
    STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"
else:
    STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

STORAGES = { "staticfiles": { "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage" } }

import os
from pathlib import Path
import environ
from dotenv import load_dotenv

load_dotenv()

# Initialize environment variables
env = environ.Env()

BASE_DIR = Path(__file__).resolve().parent.parent

# Read .env file
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

# SECURITY
SECRET_KEY = env('SECRET_KEY', default='django-insecure-change-this-key-in-production')

# 🔥 FORCE DEBUG TRUE FOR DEVELOPMENT
DEBUG = True

ALLOWED_HOSTS = ['*']

CSRF_TRUSTED_ORIGINS = [
    "https://demo1.rubixeprojects.com",
    "https://www.demo1.rubixeprojects.com",
    "http://demo1.rubixeprojects.com",
    "http://www.demo1.rubixeprojects.com",
]

# APPLICATIONS
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_extensions',

    # Local apps
    'user_management',
    'interview_system',
]

# MIDDLEWARE
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'mock_interview_platform.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'mock_interview_platform.wsgi.application'

# DATABASE
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# PASSWORD VALIDATION
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# INTERNATIONALIZATION
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

# 🔥 STATIC FILES (DEV SAFE CONFIG)
STATIC_URL = '/static/'

# ❌ DO NOT SET STATIC_ROOT in development
# ❌ DO NOT SET STATICFILES_DIRS unless needed

# MEDIA FILES
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# DEFAULT PK
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# CUSTOM USER
AUTH_USER_MODEL = 'user_management.CustomUser'

# LOGIN CONFIG
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/login/'

# HDFS CONFIG
HDFS_CONFIG = {
    'HOST': env('HDFS_HOST', default='localhost'),
    'PORT': env('HDFS_PORT', default='9870'),
    'USER': env('HDFS_USER', default='hdfs'),
    'QUESTIONS_DIR': '/questions',
    'RESPONSES_DIR': '/responses',
    'FRAMES_DIR': '/frames',
}

# OPENROUTER CONFIG
OPENROUTER_CONFIG = {
    'API_KEY': env('OPENROUTER_API_KEY', default=''),
    'BASE_URL': 'https://openrouter.ai/api/v1',
    'MODEL': 'deepseek/deepseek-r1-0528',
}

GEMINI_API_KEY = env('GEMINI_API_KEY', default='')

STT_CONFIG = {
    'PROVIDER': env('STT_PROVIDER', default='faster_whisper'),
    'MODEL_SIZE': env('WHISPER_MODEL_SIZE', default='tiny.en'),
    'DEVICE': env('WHISPER_DEVICE', default='cpu'),
    'COMPUTE_TYPE': env('WHISPER_COMPUTE_TYPE', default='int8'),
    'CPU_THREADS': env.int('WHISPER_CPU_THREADS', default=4),
    'NUM_WORKERS': env.int('WHISPER_NUM_WORKERS', default=1),
    'LANGUAGE': env('WHISPER_LANGUAGE', default='en'),
}

VOICE_INTERVIEW_TTS_ENABLED = env.bool('VOICE_INTERVIEW_TTS_ENABLED', default=True)

if not GEMINI_API_KEY:
    print("⚠️ WARNING: GEMINI_API_KEY is not set in .env file")
else:
    print("✅ GEMINI_API_KEY loaded successfully")

# LOGGING
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}

DATA_UPLOAD_MAX_MEMORY_SIZE = 50 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 50 * 1024 * 1024

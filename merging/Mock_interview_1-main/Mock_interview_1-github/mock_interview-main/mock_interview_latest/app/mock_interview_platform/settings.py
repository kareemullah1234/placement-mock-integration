import os
import importlib.util
from pathlib import Path
from dotenv import load_dotenv

try:
    import environ
except ModuleNotFoundError:
    environ = None

BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env file if present
load_dotenv(os.path.join(BASE_DIR, ".env"))

if environ is not None:
    env = environ.Env()
    environ.Env.read_env(os.path.join(BASE_DIR, ".env"))
else:
    class _FallbackEnv:
        def __call__(self, key, default=None):
            return os.getenv(key, default)

        def int(self, key, default=0):
            value = os.getenv(key)
            if value is None or value == "":
                return default
            try:
                return int(value)
            except ValueError:
                return default

        def bool(self, key, default=False):
            value = os.getenv(key)
            if value is None or value == "":
                return default
            return value.strip().lower() in {"1", "true", "t", "yes", "y", "on"}

    env = _FallbackEnv()

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

    # Local apps
    'user_management',
    'interview_system',
]

if importlib.util.find_spec("django_extensions") is not None:
    INSTALLED_APPS.append("django_extensions")

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

# KAFKA CONFIG
def _split_csv(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]

RUNNING_IN_DOCKER = Path("/.dockerenv").exists()
_DEFAULT_KAFKA_BOOTSTRAP = "kafka-frames:29092" if RUNNING_IN_DOCKER else "127.0.0.1:9092"

KAFKA_CONFIG = {
    "bootstrap_servers": _split_csv(env("KAFKA_BOOTSTRAP_SERVERS", default=_DEFAULT_KAFKA_BOOTSTRAP)),
    "frame_topic": env("KAFKA_FRAME_TOPIC", default="interview-frames"),
    "video_topic": env("KAFKA_VIDEO_TOPIC", default="interview-videos"),
    "timeout": env.int("KAFKA_TIMEOUT", default=10),
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
    print("WARNING: GEMINI_API_KEY is not set in .env file")
else:
    print("GEMINI_API_KEY loaded successfully")

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

"""
KING CH - Settings
  - En local (DEBUG=True)  : python manage.py runserver -> http://127.0.0.1:8000
  - En production (Render) : DEBUG=False via variable d environnement
"""
from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

# ── Secret key ────────────────────────────────────────────────────────────────
SECRET_KEY = os.environ.get(
    'SECRET_KEY',
    'django-insecure-kingch-local-dev-key-change-in-prod-2024'
)

# ── Debug ─────────────────────────────────────────────────────────────────────
# CORRECTION : on teste si DEBUG est explicitement False/false/0/no
# car la comparaison precedente ratait quand Render envoyait 'False' (majuscule)
_debug_env = os.environ.get('DEBUG', 'True').strip().lower()
DEBUG = _debug_env not in ('false', '0', 'no', 'off')

# ── Hosts & CSRF ──────────────────────────────────────────────────────────────
if DEBUG:
    ALLOWED_HOSTS = ['*']
    CSRF_TRUSTED_ORIGINS = ['http://localhost:8000', 'http://127.0.0.1:8000']
else:
    ALLOWED_HOSTS = os.environ.get(
        'ALLOWED_HOSTS', '.onrender.com,localhost,127.0.0.1'
    ).split(',')
    CSRF_TRUSTED_ORIGINS = ['https://*.onrender.com']
    # Ajoute chaque host de ALLOWED_HOSTS
    for _h in ALLOWED_HOSTS:
        _h = _h.strip()
        if _h and _h not in ('.onrender.com',):
            _origin = f"https://{_h.lstrip('.')}"
            if _origin not in CSRF_TRUSTED_ORIGINS:
                CSRF_TRUSTED_ORIGINS.append(_origin)

# ── Apps ──────────────────────────────────────────────────────────────────────
INSTALLED_APPS = [
    'jazzmin',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'quiz',
]

# ── Middleware ────────────────────────────────────────────────────────────────
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'quiz.middleware.BlockedUserMiddleware',
    'quiz.middleware.SecurityHeadersMiddleware',
    'quiz.middleware.RateLimitMiddleware',
]

ROOT_URLCONF = 'kingch_project.urls'

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
                'quiz.context_processors.global_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'kingch_project.wsgi.application'

# ── Base de donnees ───────────────────────────────────────────────────────────
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

if os.environ.get('DATABASE_URL'):
    import dj_database_url
    DATABASES['default'] = dj_database_url.config(
        default=os.environ['DATABASE_URL'],
        conn_max_age=600,
        ssl_require=not DEBUG,
    )

# ── Auth ──────────────────────────────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LOGIN_URL           = '/login/'
LOGIN_REDIRECT_URL  = '/dashboard/'
LOGOUT_REDIRECT_URL = '/login/'

# ── Internationalisation ──────────────────────────────────────────────────────
LANGUAGE_CODE = 'fr-fr'
TIME_ZONE     = 'America/Port-au-Prince'
USE_I18N      = True
USE_TZ        = True

# ── Fichiers statiques ────────────────────────────────────────────────────────
STATIC_URL  = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

if DEBUG:
    STATICFILES_DIRS = [BASE_DIR / 'static']
    STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'
else:
    _static_dir = BASE_DIR / 'static'
    if _static_dir.exists():
        STATICFILES_DIRS = [_static_dir]
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL  = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ── Stockage des fichiers media (Cloudinary ou Backblaze B2) ─────────────────
def _clean_cloudinary_url(raw):
    if not raw:
        return None
    url = raw.strip().strip('"').strip("'")
    if not url:
        return None
    if url.startswith('cloudinary:') and not url.startswith('cloudinary://'):
        url = 'cloudinary://' + url[len('cloudinary:'):]
    elif not url.startswith('cloudinary://'):
        url = 'cloudinary://' + url
    body = url[len('cloudinary://'):]
    if '@' not in body or ':' not in body.split('@')[0]:
        return None
    return url


_cloudinary_raw   = os.environ.get('CLOUDINARY_URL', '')
_cloudinary_clean = _clean_cloudinary_url(_cloudinary_raw)

if _cloudinary_raw and not _cloudinary_clean:
    print(
        "[KING CH] ATTENTION: CLOUDINARY_URL mal formee. "
        "Format: cloudinary://API_KEY:API_SECRET@CLOUD_NAME"
    )

if _cloudinary_clean:
    os.environ['CLOUDINARY_URL'] = _cloudinary_clean
    INSTALLED_APPS += ['cloudinary_storage', 'cloudinary']
    DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'
    print("[KING CH] Cloudinary actif — images persistantes.")

elif os.environ.get('B2_ACCESS_KEY_ID'):
    INSTALLED_APPS += ['storages']
    AWS_ACCESS_KEY_ID        = os.environ.get('B2_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY    = os.environ.get('B2_SECRET_ACCESS_KEY')
    AWS_STORAGE_BUCKET_NAME  = os.environ.get('B2_BUCKET_NAME')
    AWS_S3_ENDPOINT_URL      = os.environ.get('B2_ENDPOINT_URL')
    AWS_S3_REGION_NAME       = os.environ.get('B2_REGION', 'us-west-004')
    AWS_DEFAULT_ACL          = 'public-read'
    AWS_QUERYSTRING_AUTH     = False
    AWS_S3_FILE_OVERWRITE    = False
    AWS_S3_SIGNATURE_VERSION = 's3v4'
    DEFAULT_FILE_STORAGE     = 'storages.backends.s3boto3.S3Boto3Storage'
    MEDIA_URL = f"{AWS_S3_ENDPOINT_URL}/{AWS_STORAGE_BUCKET_NAME}/"
    print("[KING CH] Backblaze B2 actif — images persistantes.")

else:
    if not DEBUG:
        print("[KING CH] ATTENTION: Pas de stockage cloud configure. "
              "Les images seront perdues au prochain redemarrage.")

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ── Timer quiz (secondes par question) ───────────────────────────────────────
QUIZ_TIMER_SECONDS = int(os.environ.get('QUIZ_TIMER_SECONDS', '10'))

# ── Email ─────────────────────────────────────────────────────────────────────
EMAIL_BACKEND   = 'django.core.mail.backends.console.EmailBackend'
WHATSAPP_NUMBER = os.environ.get('WHATSAPP_NUMBER', '50938000000')

# ── Session ───────────────────────────────────────────────────────────────────
SESSION_COOKIE_AGE              = 86400
SESSION_EXPIRE_AT_BROWSER_CLOSE = False

# ── Securite production ───────────────────────────────────────────────────────
if not DEBUG:
    SECURE_SSL_REDIRECT            = True
    SECURE_HSTS_SECONDS            = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD            = True
    SECURE_CONTENT_TYPE_NOSNIFF    = True
    SECURE_BROWSER_XSS_FILTER      = True
    X_FRAME_OPTIONS                = 'DENY'
    CSRF_COOKIE_SECURE             = True
    SESSION_COOKIE_SECURE          = True
    SESSION_COOKIE_HTTPONLY        = True
    CSRF_COOKIE_HTTPONLY           = True

# ── Jazzmin ───────────────────────────────────────────────────────────────────
JAZZMIN_SETTINGS = {
    "site_title":        "KING CH Admin",
    "site_header":       "KING CH",
    "site_brand":        "KING CH",
    "site_logo":         "images/manno.png",
    "login_logo":        None,
    "login_logo_dark":   None,
    "site_logo_classes": "img-circle elevation-3",
    "site_icon":         "images/manno.png",
    "welcome_sign":      "Bienvenue dans le panneau KING CH",
    "copyright":         "KING CH — Cree par Emmanuel Christopher Badio",
    "search_model":      ["auth.user", "quiz.DailyQuestion"],
    "user_avatar":       None,
    "topmenu_links": [
        {"name": "Tableau de bord", "url": "admin:index", "permissions": ["auth.view_user"]},
        {"name": "Voir le site",    "url": "/",           "new_window": True},
        {"model": "auth.User"},
    ],
    "usermenu_links": [
        {"name": "Voir le site", "url": "/", "new_window": True, "icon": "fas fa-globe"},
        {"model": "auth.user"},
    ],
    "show_sidebar":        True,
    "navigation_expanded": True,
    "hide_apps":    [],
    "hide_models":  [],
    "order_with_respect_to": [
        "auth", "quiz",
        "quiz.UserProfile", "quiz.DailyQuestion",
        "quiz.UserAnswer", "quiz.Certificate", "quiz.Notification",
    ],
    "icons": {
        "auth":               "fas fa-users-cog",
        "auth.user":          "fas fa-user",
        "auth.Group":         "fas fa-users",
        "quiz.UserProfile":   "fas fa-id-card",
        "quiz.DailyQuestion": "fas fa-question-circle",
        "quiz.UserAnswer":    "fas fa-check-circle",
        "quiz.Certificate":   "fas fa-award",
        "quiz.Notification":  "fas fa-bell",
    },
    "default_icon_parents":  "fas fa-chevron-circle-right",
    "default_icon_children": "fas fa-circle",
    "related_modal_active":  True,
    "custom_css":            "css/jazzmin_custom.css",
    "custom_js":             None,
    "use_google_fonts_cdn":  True,
    "show_ui_builder":       False,
    "changeform_format":     "horizontal_tabs",
    "changeform_format_overrides": {
        "auth.user":  "collapsible",
        "auth.group": "vertical_tabs",
    },
    "language_chooser": False,
}

JAZZMIN_UI_TWEAKS = {
    "navbar_small_text":         False,
    "footer_small_text":         True,
    "body_small_text":           False,
    "brand_small_text":          False,
    "brand_colour":              "navbar-dark",
    "accent":                    "accent-warning",
    "navbar":                    "navbar-dark navbar-kingch",
    "no_navbar_border":          True,
    "navbar_fixed":              True,
    "layout_boxed":              False,
    "footer_fixed":              False,
    "sidebar_fixed":             True,
    "sidebar":                   "sidebar-dark-warning",
    "sidebar_nav_small_text":    False,
    "sidebar_disable_expand":    False,
    "sidebar_nav_child_indent":  True,
    "sidebar_nav_compact_style": False,
    "sidebar_nav_legacy_style":  False,
    "sidebar_nav_flat_style":    False,
    "theme":                     "darkly",
    "dark_mode_theme":           "darkly",
    "button_classes": {
        "primary":   "btn-primary",
        "secondary": "btn-secondary",
        "info":      "btn-info",
        "warning":   "btn-warning",
        "danger":    "btn-danger",
        "success":   "btn-success",
    },
}

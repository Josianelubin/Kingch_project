from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# NOTE: do NOT set admin.site.site_header here — Jazzmin handles it via settings.py
# Setting it here would override Jazzmin settings.

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('quiz.urls')),
]

# Sert les fichiers media en local (DEBUG) ou si Cloudinary n'est pas configure.
# Sans danger meme avec Cloudinary actif : les nouvelles images utilisent
# une URL Cloudinary externe, cette route ne sert que d'ancien fallback local.
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

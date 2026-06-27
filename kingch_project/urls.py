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

# Serve media files in development (DEBUG=True)
# In production (Render), use a CDN or cloud storage
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    # Still serve media in production for simplicity (Render ephemeral disk)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

admin.site.site_header = "KING CH - Administration"
admin.site.site_title = "KING CH Admin"
admin.site.index_title = "Tableau de bord KING CH"

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('quiz.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

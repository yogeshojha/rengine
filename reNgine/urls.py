from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('dashboard.urls')),
    path('target/', include('targetApp.urls')),
    path('scanEngine/', include('scanEngine.urls')),
    path('start_scan/', include('startScan.urls')),
    path('notification/', include('notification.urls')),

    # REST-framework
    path('api/scannedHost/', include('startScan.api.urls', 'scan_host_api')),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

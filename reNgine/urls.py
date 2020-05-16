from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('dashboard.urls')),
    path('target/', include('targetApp.urls')),
    path('scanEngine/', include('scanEngine.urls')),
    path('start_scan/', include('startScan.urls')),
]

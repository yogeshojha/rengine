from django.urls import path
from startScan.api.views import api_scan_host_detailed_view

app_name = 'startScan'
urlpatterns = [
    path('<id>/', api_scan_host_detailed_view, name='detail'),
]

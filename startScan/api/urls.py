from django.conf.urls import url, include
from django.urls import path
from rest_framework import routers
from .views import ScanHistoryViewSet, api_scan_host_detailed_view

app_name = 'startScan'
router = routers.DefaultRouter()

router.register(r'scanHistory', ScanHistoryViewSet)

urlpatterns = [
    url('^', include(router.urls)),
    path('detail/<id>/', api_scan_host_detailed_view)

]

urlpatterns += router.urls

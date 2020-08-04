from django.conf.urls import url, include
from django.urls import path
from rest_framework import routers
from .views import ScanHistoryViewSet, EndPointViewSet, VulnerabilityScannerViewSet

app_name = 'startScan'
router = routers.DefaultRouter()

router.register(r'scanHistory', ScanHistoryViewSet)

router.register(r'listEndpoints', EndPointViewSet)

router.register(r'listVulnerability', VulnerabilityScannerViewSet)

urlpatterns = [
    url('^', include(router.urls)),

]

urlpatterns += router.urls

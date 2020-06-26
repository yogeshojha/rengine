from django.conf.urls import url, include
from django.urls import path
from rest_framework import routers
from .views import ScanHistoryViewSet

app_name = 'startScan'
router = routers.DefaultRouter()

router.register(r'scanHistory', ScanHistoryViewSet)

urlpatterns = [
    url('^', include(router.urls)),

]

urlpatterns += router.urls

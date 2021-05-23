from django.conf.urls import url, include
from django.urls import path
from rest_framework import routers
from .views import *

app_name = 'startScan'
router = routers.DefaultRouter()

router.register(r'scanHistory', SubdomainViewset)

router.register(r'listEndpoints', EndPointViewSet)

router.register(r'listVulnerability', VulnerabilityViewSet)

router.register(r'listInterestingSubdomains', InterestingSubdomainViewSet)

router.register(r'listInterestingEndpoints', InterestingEndpointViewSet)

router.register(r'listSubdomainChanges', SubdomainChangesViewSet)

router.register(r'listEndPointChanges', EndPointChangesViewSet)

urlpatterns = [
    url('^', include(router.urls)),

]

urlpatterns += router.urls

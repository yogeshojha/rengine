from django.conf.urls import url, include
from django.urls import path
from rest_framework import routers
from .views import *

app_name = 'startScan'
router = routers.DefaultRouter()

router.register(r'scanHistory', SubdomainViewset)

router.register(r'listSubdomains', ListSubdomainsViewSet)

router.register(r'listEndpoints', EndPointViewSet)

router.register(r'listVulnerability', VulnerabilityViewSet)

router.register(r'listInterestingSubdomains', InterestingSubdomainViewSet)

router.register(r'listInterestingEndpoints', InterestingEndpointViewSet)

router.register(r'listSubdomainChanges', SubdomainChangesViewSet)

router.register(r'listEndPointChanges', EndPointChangesViewSet)

router.register(r'listIps', IpAddressViewSet)

urlpatterns = [
    url('^', include(router.urls)),
    path('listTechnologies/', ListTechnology.as_view(), name='listTechnologies'),
    path('listPorts/', ListPorts.as_view(), name='listPorts'),
    path('listIPs/', ListIPs.as_view(), name='listIPs'),
]

urlpatterns += router.urls

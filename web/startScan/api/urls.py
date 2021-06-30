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
    path('queryTechnologies/', ListTechnology.as_view(), name='listTechnologies'),
    path('queryPorts/', ListPorts.as_view(), name='listPorts'),
    path('queryIps/', ListIPs.as_view(), name='listIPs'),
    path('querySubdomains/', ListSubdomains.as_view(), name='querySubdomains'),
    path('queryOsintUsers/', ListOsintUsers.as_view(), name='queryOsintUsers'),
    path('queryMetadata/', ListMetadata.as_view(), name='queryMetadata'),
    path('queryEmails/', ListEmails.as_view(), name='queryEmails'),
    path('queryEmployees/', ListEmployees.as_view(), name='queryEmployees'),
    path('queryDorks/', ListDorks.as_view(), name='queryDorks'),
    path('queryDorkTypes/', ListDorkTypes.as_view(), name='queryDorkTypes'),
    path('queryAllScanResultMitch/', MitchData.as_view(), name='queryAllScanResultMitch'),
]

urlpatterns += router.urls

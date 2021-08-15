from django.conf.urls import url, include
from django.urls import path
from rest_framework import routers
from .views import *

app_name = 'api'
router = routers.DefaultRouter()

router.register(r'listDatatableSubdomain', SubdomainDatatableViewSet)

router.register(r'listSubdomains', SubdomainsViewSet)

router.register(r'listEndpoints', EndPointViewSet)

router.register(r'listVulnerability', VulnerabilityViewSet)

router.register(r'listInterestingSubdomains', InterestingSubdomainViewSet)

router.register(r'listInterestingEndpoints', InterestingEndpointViewSet)

router.register(r'listSubdomainChanges', SubdomainChangesViewSet)

router.register(r'listEndPointChanges', EndPointChangesViewSet)

router.register(r'listIps', IpAddressViewSet)

urlpatterns = [
    url('^', include(router.urls)),
    path(
        'queryTechnologies/',
        ListTechnology.as_view(),
        name='listTechnologies'),
    path(
        'queryPorts/',
        ListPorts.as_view(),
        name='listPorts'),
    path(
        'queryIps/',
        ListIPs.as_view(),
        name='listIPs'),
    path(
        'querySubdomains/',
        ListSubdomains.as_view(),
        name='querySubdomains'),
    path(
        'queryOsintUsers/',
        ListOsintUsers.as_view(),
        name='queryOsintUsers'),
    path(
        'queryMetadata/',
        ListMetadata.as_view(),
        name='queryMetadata'),
    path(
        'queryEmails/',
        ListEmails.as_view(),
        name='queryEmails'),
    path(
        'queryEmployees/',
        ListEmployees.as_view(),
        name='queryEmployees'),
    path(
        'queryDorks/',
        ListDorks.as_view(),
        name='queryDorks'),
    path(
        'queryDorkTypes/',
        ListDorkTypes.as_view(),
        name='queryDorkTypes'),
    path(
        'queryDorkTypes/',
        ListDorkTypes.as_view(),
        name='queryDorkTypes'),
    path(
        'queryAllScanResultVisualise/',
        VisualiseData.as_view(),
        name='queryAllScanResultVisualise'),
    path(
        'queryVulnerabilities/',
        ListVulnerability.as_view(),
        name='queryVulnerabilities'),
    path(
        'queryEndpoints/',
        ListEndpoints.as_view(),
        name='queryEndpoints'),
    path(
        'queryTargetsWithoutOrganization/',
        ListTargetsWithoutOrganization.as_view(),
        name='queryTargetsWithoutOrganization'),
    path(
        'queryTargetsInOrganization/',
        ListTargetsInOrganization.as_view(),
        name='queryTargetsInOrganization'),
    path(
        'listOrganizations/',
        ListOrganizations.as_view(),
        name='listOrganizations'),
    path(
        'listEngines/',
        ListEngines.as_view(),
        name='listEngines'),
    path(
        'listScanHistory/',
        ListScanHistory.as_view(),
        name='listScanHistory'),
    path(
        'listTodoNotes/',
        ListTodoNotes.as_view(),
        name='listTodoNotes'),
    path(
        'getFileContents/',
        GetFileContents.as_view(),
        name='getFileContents'),
    path(
        'vulnerability/report/',
        VulnerabilityReport.as_view(),
        name='vulnerability_report'),
]

urlpatterns += router.urls

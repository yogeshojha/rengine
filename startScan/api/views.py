from startScan.api.serializers import ScanHistorySerializer, EndpointSerializer, VulnerabilitySerializer
from rest_framework import viewsets
from startScan.models import ScannedHost, ScanHistory, WayBackEndPoint, VulnerabilityScan
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view, action
from django.db.models import Q


class ScanHistoryViewSet(viewsets.ModelViewSet):
    queryset = ScannedHost.objects.all()
    serializer_class = ScanHistorySerializer

    def get_queryset(self):
        req = self.request
        scan_id = req.query_params.get('scan_id')
        if scan_id:
            self.queryset = ScannedHost.objects.filter(
                scan_history__id=scan_id)
            return self.queryset
        else:
            return self.queryset


class EndPointViewSet(viewsets.ModelViewSet):
    queryset = WayBackEndPoint.objects.all()
    serializer_class = EndpointSerializer

    def get_queryset(self):
        req = self.request
        url_of = req.query_params.get('url_of')
        if url_of:
            self.queryset = WayBackEndPoint.objects.filter(url_of__id=url_of)
            return self.queryset
        else:
            return self.queryset


class VulnerabilityViewSet(viewsets.ModelViewSet):
    queryset = VulnerabilityScan.objects.all()
    serializer_class = VulnerabilitySerializer

    def get_queryset(self):
        req = self.request
        vulnerability_of = req.query_params.get('vulnerability_of')
        url_query = req.query_params.get('query_param')
        if url_query:
            self.queryset = VulnerabilityScan.objects.filter(
                Q(vulnerability_of__domain_name__domain_name=url_query) | Q(name=url_query))
        elif vulnerability_of:
            self.queryset = VulnerabilityScan.objects.filter(
                vulnerability_of__id=vulnerability_of)
        return self.queryset

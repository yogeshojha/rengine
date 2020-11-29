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
            if url_query.isnumeric():
                self.queryset = VulnerabilityScan.objects.filter(
                    Q(
                        vulnerability_of__domain_name__domain_name=url_query) | Q(
                        name=url_query) | Q(
                        id=url_query))
            else:
                self.queryset = VulnerabilityScan.objects.filter(
                    Q(vulnerability_of__domain_name__domain_name=url_query) | Q(name=url_query))
        elif vulnerability_of:
            self.queryset = VulnerabilityScan.objects.filter(
                vulnerability_of__id=vulnerability_of)
        return self.queryset

    def filter_queryset(self, qs):
        search_value = self.request.GET.get(u'search[value]', None)
        # if the search query is separated by : means, it is a specific lookup
        # divide the search query into two half and lookup
        if ':' in search_value:
            search_param = search_value.split("=")
            lookup_title = search_param[0].lower()
            lookup_content = search_param[1].lower()
            if 'severity' in lookup_title:
                return self.queryset.filter(severity__icontains=lookup_content)
            elif 'title' in lookup_title:
                return self.queryset.filter(name__icontains=lookup_content)
            elif 'status' in lookup_title:
                if lookup_content == 'open':
                    return self.queryset.filter(open_status=True)
                elif lookup_content == 'closed':
                    return self.queryset.filter(open_status=False)
            elif 'description' in lookup_title:
                return self.queryset.filter(
                    Q(
                        description__icontains=lookup_content) | Q(
                        template_used__icontains=lookup_content) | Q(
                        extracted_results__icontains=lookup_content) | Q(
                        matcher_name__icontains=lookup_content))
        else:
            qs = self.queryset.filter(Q(discovered_date__icontains=search_value)
                    | Q(url__icontains=search_value)
                    | Q(name__icontains=search_value)
                    | Q(severity__icontains=search_value)
                    | Q(description__icontains=search_value)
                    | Q(extracted_results__icontains=search_value)
                    | Q(template_used__icontains=search_value)
                    | Q(matcher_name__icontains=search_value))
        return qs

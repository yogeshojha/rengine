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

    def filter_queryset(self, qs):
        qs = self.queryset.filter()
        search_value = self.request.GET.get(u'search[value]', None)
        _order_col = self.request.GET.get(u'order[0][column]', None)
        _order_direction = self.request.GET.get(u'order[0][dir]', None)
        order_col = 'content_length'
        if _order_col == '0':
            order_col = 'checked'
        elif _order_col == '1':
            order_col = 'subdomain'
        elif _order_col == '2':
            order_col = 'ip_address'
        elif _order_col == '3':
            order_col = 'http_status'
        elif _order_col == '4':
            order_col = 'open_ports'
        elif _order_col == '5':
            order_col = 'content_length'
        elif _order_col == '6':
            order_col = 'page_title'
        elif _order_col == '6':
            order_col = 'technology_stack'
        if _order_direction == 'desc':
            order_col = '-{}'.format(order_col)
        # if the search query is separated by = means, it is a specific lookup
        # divide the search query into two half and lookup
        if '=' in search_value or '&' in search_value or '|' in search_value or '>' in search_value or '<' in search_value or '!' in search_value:
            if '&' in search_value:
                complex_query = search_value.split('&')
                for query in complex_query:
                    if query.strip():
                        qs = qs & self.special_lookup(query.strip())
            elif '|' in search_value:
                qs = ScannedHost.objects.none()
                complex_query = search_value.split('|')
                for query in complex_query:
                    if query.strip():
                        qs = self.special_lookup(query.strip()) | qs
            else:
                qs = self.special_lookup(search_value)
        else:
            qs = self.general_lookup(search_value)
        return qs.order_by(order_col)

    def general_lookup(self, search_value):
        qs = self.queryset.filter(
            Q(discovered_date__icontains=search_value) |
            Q(subdomain__icontains=search_value) |
            Q(cname__icontains=search_value) |
            Q(open_ports__icontains=search_value) |
            Q(http_status__icontains=search_value) |
            Q(content_length__icontains=search_value) |
            Q(page_title__icontains=search_value) |
            Q(http_url__icontains=search_value) |
            Q(ip_address__icontains=search_value) |
            Q(is_ip_cdn__icontains=search_value) |
            Q(screenshot_path__icontains=search_value) |
            Q(http_header_path__icontains=search_value) |
            Q(technology_stack__icontains=search_value) |
            Q(directory_json__icontains=search_value) |
            Q(checked__icontains=search_value) |
            Q(discovered_date__icontains=search_value))

        return qs

    def special_lookup(self, search_value):
        qs = self.queryset.filter()
        print(search_value)
        if '=' in search_value:
            search_param = search_value.split("=")
            lookup_title = search_param[0].lower().strip()
            lookup_content = search_param[1].lower().strip()
            if 'subdomain' in lookup_title:
                qs = self.queryset.filter(subdomain__icontains=lookup_content)
            elif 'cname' in lookup_title:
                qs = self.queryset.filter(cname__icontains=lookup_content)
            elif 'ports' in lookup_title or 'open_ports' in lookup_title:
                qs = self.queryset.filter(open_ports__icontains=lookup_content)
            elif 'ip_address' in lookup_title or 'ip' in lookup_title:
                qs = self.queryset.filter(ip_address__icontains=lookup_content)
            elif 'tech' in lookup_title or 'technology' in lookup_title or 'technology_stack' in lookup_title:
                qs = self.queryset.filter(
                    technology_stack__icontains=lookup_content)
            elif 'http_status' in lookup_title:
                try:
                    int_http_status = int(lookup_content)
                    qs = self.queryset.filter(http_status=int_http_status)
                except Exception as e:
                    print(e)
            elif 'content_length' in lookup_title:
                try:
                    int_http_status = int(lookup_content)
                    qs = self.queryset.filter(content_length=int_http_status)
                except Exception as e:
                    print(e)
            elif 'cdn' in lookup_title:
                if lookup_content == 'true':
                    qs = self.queryset.filter(is_ip_cdn=True)
                elif lookup_content == 'false':
                    qs = self.queryset.filter(is_ip_cdn=False)
            elif 'status' in lookup_title:
                if lookup_content == 'open':
                    qs = self.queryset.filter(checked=False)
                elif lookup_content == 'closed':
                    qs = self.queryset.filter(checked=True)
        elif '>' in search_value:
            search_param = search_value.split(">")
            lookup_title = search_param[0].lower().strip()
            lookup_content = search_param[1].lower().strip()
            if 'http_status' in lookup_title:
                try:
                    int_val = int(lookup_content)
                    qs = self.queryset.filter(http_status__gt=int_val)
                except Exception as e:
                    print(e)
            elif 'content_length' in lookup_title:
                try:
                    int_val = int(lookup_content)
                    qs = self.queryset.filter(content_length__gt=int_val)
                except Exception as e:
                    print(e)
        elif '<' in search_value:
            search_param = search_value.split("<")
            lookup_title = search_param[0].lower().strip()
            lookup_content = search_param[1].lower().strip()
            if 'http_status' in lookup_title:
                try:
                    int_val = int(lookup_content)
                    qs = self.queryset.filter(http_status__lt=int_val)
                except Exception as e:
                    print(e)
            elif 'content_length' in lookup_title:
                try:
                    int_val = int(lookup_content)
                    qs = self.queryset.filter(content_length__lt=int_val)
                except Exception as e:
                    print(e)
        elif '!' in search_value:
            search_param = search_value.split("!")
            lookup_title = search_param[0].lower().strip()
            lookup_content = search_param[1].lower().strip()
            if 'subdomain' in lookup_title:
                qs = self.queryset.exclude(subdomain__icontains=lookup_content)
            elif 'cname' in lookup_title:
                qs = self.queryset.exclude(cname__icontains=lookup_content)
            elif 'ports' in lookup_title or 'open_ports' in lookup_title:
                qs = self.queryset.exclude(
                    open_ports__icontains=lookup_content)
            elif 'ip_address' in lookup_title or 'ip' in lookup_title:
                qs = self.queryset.exclude(
                    ip_address__icontains=lookup_content)
            elif 'tech' in lookup_title or 'technology' in lookup_title or 'technology_stack' in lookup_title:
                qs = self.queryset.exclude(
                    technology_stack__icontains=lookup_content)
            elif 'http_status' in lookup_title:
                try:
                    int_http_status = int(lookup_content)
                    qs = self.queryset.exclude(http_status=int_http_status)
                except Exception as e:
                    print(e)
            elif 'cdn' in lookup_title:
                if lookup_content == 'true':
                    qs = self.queryset.exclude(is_ip_cdn=True)
                elif lookup_content == 'false':
                    qs = self.queryset.exclude(is_ip_cdn=False)
            elif 'status' in lookup_title:
                if lookup_content == 'open':
                    qs = self.queryset.exclude(checked=False)
                elif lookup_content == 'closed':
                    qs = self.queryset.exclude(checked=True)
        return qs


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

    def filter_queryset(self, qs):
        qs = self.queryset.filter()
        search_value = self.request.GET.get(u'search[value]', None)
        _order_col = self.request.GET.get(u'order[0][column]', None)
        _order_direction = self.request.GET.get(u'order[0][dir]', None)
        order_col = 'content_length'
        if _order_col == '0':
            order_col = 'http_url'
        elif _order_col == '1':
            order_col = 'http_status'
        elif _order_col == '2':
            order_col = 'content_type'
        elif _order_col == '3':
            order_col = 'content_length'
        elif _order_col == '4':
            order_col = 'page_title'
        if _order_direction == 'desc':
            order_col = '-{}'.format(order_col)
        # if the search query is separated by = means, it is a specific lookup
        # divide the search query into two half and lookup
        if '=' in search_value or '&' in search_value or '|' in search_value or '>' in search_value or '<' in search_value or '!' in search_value:
            if '&' in search_value:
                complex_query = search_value.split('&')
                for query in complex_query:
                    if query.strip():
                        qs = qs & self.special_lookup(query.strip())
            elif '|' in search_value:
                qs = ScannedHost.objects.none()
                complex_query = search_value.split('|')
                for query in complex_query:
                    if query.strip():
                        qs = self.special_lookup(query.strip()) | qs
            else:
                qs = self.special_lookup(search_value)
        else:
            qs = self.general_lookup(search_value)
        return qs.order_by(order_col)

    def general_lookup(self, search_value):
        qs = self.queryset.filter(
            Q(http_url__icontains=search_value) |
            Q(content_length__icontains=search_value) |
            Q(page_title__icontains=search_value) |
            Q(http_status__icontains=search_value) |
            Q(content_type__icontains=search_value) |
            Q(discovered_date__icontains=search_value))
        return qs

    def special_lookup(self, search_value):
        qs = self.queryset.filter()
        print(search_value)
        if '=' in search_value:
            search_param = search_value.split("=")
            lookup_title = search_param[0].lower().strip()
            lookup_content = search_param[1].lower().strip()
            if 'url' in lookup_title or 'http_url' in lookup_title:
                qs = self.queryset.filter(http_url__icontains=lookup_content)
            elif 'http_status' in lookup_title:
                try:
                    int_http_status = int(lookup_content)
                    qs = self.queryset.filter(http_status=int_http_status)
                except Exception as e:
                    print(e)
            elif 'content_length' in lookup_title:
                try:
                    int_http_status = int(lookup_content)
                    qs = self.queryset.filter(content_length=int_http_status)
                except Exception as e:
                    print(e)
            elif 'content_type' in lookup_title or 'ip' in lookup_title:
                qs = self.queryset.filter(content_type__icontains=lookup_content)
        elif '>' in search_value:
            search_param = search_value.split(">")
            lookup_title = search_param[0].lower().strip()
            lookup_content = search_param[1].lower().strip()
            if 'http_status' in lookup_title:
                try:
                    int_val = int(lookup_content)
                    qs = self.queryset.filter(http_status__gt=int_val)
                except Exception as e:
                    print(e)
            elif 'content_length' in lookup_title:
                try:
                    int_val = int(lookup_content)
                    qs = self.queryset.filter(content_length__gt=int_val)
                except Exception as e:
                    print(e)
        elif '<' in search_value:
            search_param = search_value.split("<")
            lookup_title = search_param[0].lower().strip()
            lookup_content = search_param[1].lower().strip()
            if 'http_status' in lookup_title:
                try:
                    int_val = int(lookup_content)
                    qs = self.queryset.filter(http_status__lt=int_val)
                except Exception as e:
                    print(e)
            elif 'content_length' in lookup_title:
                try:
                    int_val = int(lookup_content)
                    qs = self.queryset.filter(content_length__lt=int_val)
                except Exception as e:
                    print(e)
        elif '!' in search_value:
            search_param = search_value.split("!")
            lookup_title = search_param[0].lower().strip()
            lookup_content = search_param[1].lower().strip()
            if 'url' in lookup_title or 'http_url' in lookup_title:
                qs = self.queryset.exclude(http_url__icontains=lookup_content)
            elif 'http_status' in lookup_title:
                try:
                    int_http_status = int(lookup_content)
                    qs = self.queryset.exclude(http_status=int_http_status)
                except Exception as e:
                    print(e)
            elif 'content_length' in lookup_title:
                try:
                    int_http_status = int(lookup_content)
                    qs = self.queryset.exclude(content_length=int_http_status)
                except Exception as e:
                    print(e)
            elif 'content_type' in lookup_title or 'ip' in lookup_title:
                qs = self.queryset.exclude(content_type__icontains=lookup_content)
        return qs


class VulnerabilityViewSet(viewsets.ModelViewSet):
    queryset = VulnerabilityScan.objects.all().order_by('-discovered_date')
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
        qs = self.queryset.filter()
        search_value = self.request.GET.get(u'search[value]', None)
        column = self.request.GET.get(u'order[0][column]', None)
        _order_direction = self.request.GET.get(u'order[0][dir]', None)
        order_col = 'severity'
        if column == '0':
            order_col = 'open_status'
        elif column == '1':
            order_col = 'title'
        elif column == '2':
            order_col = 'severity'
        elif column == '3':
            order_col = 'url'
        elif column == '4':
            order_col = 'description'
        elif column == '5':
            column = 'discovered_date'
        elif column == '6':
            order_col = 'open_status'
        if _order_direction == 'desc':
            order_col = '-{}'.format(order_col)
        # if the search query is separated by = means, it is a specific lookup
        # divide the search query into two half and lookup
        if '=' in search_value or '&' in search_value or '|' in search_value or '!' in search_value:
            if '&' in search_value:
                complex_query = search_value.split('&')
                for query in complex_query:
                    if query.strip():
                        qs = qs & self.special_lookup(query.strip())
            elif '|' in search_value:
                qs = VulnerabilityScan.objects.none()
                complex_query = search_value.split('|')
                for query in complex_query:
                    if query.strip():
                        qs = self.special_lookup(query.strip()) | qs
            else:
                qs = self.special_lookup(search_value)
        else:
            qs = self.general_lookup(search_value)
        return qs.order_by(order_col)

    def general_lookup(self, search_value):
        qs = self.queryset.filter(
            Q(discovered_date__icontains=search_value) |
            Q(url__icontains=search_value) |
            Q(name__icontains=search_value) |
            Q(severity__icontains=search_value) |
            Q(description__icontains=search_value) |
            Q(extracted_results__icontains=search_value) |
            Q(template_used__icontains=search_value) |
            Q(matcher_name__icontains=search_value))
        return qs

    def special_lookup(self, search_value):
        qs = self.queryset.filter()
        if '=' in search_value:
            search_param = search_value.split("=")
            lookup_title = search_param[0].lower()
            lookup_content = search_param[1].lower()
            if 'severity' in lookup_title:
                severity_value = ''
                if lookup_content == 'info':
                    severity_value = 0
                elif lookup_content == 'low':
                    severity_value = 1
                elif lookup_content == 'medium':
                    severity_value = 2
                elif lookup_content == 'high':
                    severity_value = 3
                elif lookup_content == 'critical':
                    severity_value = 4
                if severity_value:
                    qs = self.queryset.filter(severity=severity_value)
            elif 'title' in lookup_title:
                qs = self.queryset.filter(name__icontains=lookup_content)
            elif 'vulnerable_url' in lookup_title:
                qs = self.queryset.filter(url__icontains=lookup_content)
            elif 'url' in lookup_title:
                qs = self.queryset.filter(url__icontains=lookup_content)
            elif 'status' in lookup_title:
                if lookup_content == 'open':
                    qs = self.queryset.filter(open_status=True)
                elif lookup_content == 'closed':
                    qs = self.queryset.filter(open_status=False)
            elif 'description' in lookup_title:
                qs = self.queryset.filter(
                    Q(description__icontains=lookup_content) |
                    Q(template_used__icontains=lookup_content) |
                    Q(extracted_results__icontains=lookup_content) |
                    Q(matcher_name__icontains=lookup_content))
        elif '!' in search_value:
            search_param = search_value.split("!")
            lookup_title = search_param[0].lower()
            lookup_content = search_param[1].lower()
            if 'severity' in lookup_title:
                # TODO: figure out this BS
                severity_value = 5
                if lookup_content == 'info':
                    severity_value = 0
                elif lookup_content == 'low':
                    severity_value = 1
                elif lookup_content == 'medium':
                    severity_value = 2
                elif lookup_content == 'high':
                    severity_value = 3
                elif lookup_content == 'critical':
                    severity_value = 4
                print("severity_value" + str(severity_value))
                if severity_value < 5:
                    qs = self.queryset.exclude(severity=severity_value)
            elif 'title' in lookup_title:
                qs = self.queryset.exclude(name__icontains=lookup_content)
            elif 'vulnerable_url' in lookup_title:
                qs = self.queryset.exclude(url__icontains=lookup_content)
            elif 'url' in lookup_title:
                qs = self.queryset.exclude(url__icontains=lookup_content)
            elif 'status' in lookup_title:
                if lookup_content == 'open':
                    qs = self.queryset.exclude(open_status=True)
                elif lookup_content == 'closed':
                    qs = self.queryset.exclude(open_status=False)
            elif 'description' in lookup_title:
                qs = self.queryset.exclude(
                    Q(description__icontains=lookup_content) |
                    Q(template_used__icontains=lookup_content) |
                    Q(extracted_results__icontains=lookup_content) |
                    Q(matcher_name__icontains=lookup_content))
        return qs

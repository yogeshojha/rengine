import json

from startScan.api.serializers import *
from scanEngine.models import InterestingLookupModel
from startScan.models import Subdomain, ScanHistory, EndPoint, Vulnerability

from reNgine.common_func import *

from django.db.models import Q
from django.db.models import CharField, Value, Count
from django.core import serializers


from rest_framework import viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view, action


class ListTechnology(APIView):
    def get(self, request, format=None):
        req = self.request
        scan_id = req.query_params.get('scan_id')
        if scan_id:
            tech = Technology.objects.filter(
                technologies__in=Subdomain.objects.filter(
                    scan_history__id=scan_id)).annotate(
                count=Count('name')).order_by('-count')
            serializer = TechnologyCountSerializer(tech, many=True)
            return Response({"technologies": serializer.data})
        else:
            tech = Technology.objects.filter(
                technologies__in=Subdomain.objects.all()).annotate(
                count=Count('name')).order_by('-count')
            serializer = TechnologyCountSerializer(tech, many=True)
            return Response({"technologies": serializer.data})


class ListEmails(APIView):
    def get(self, request, format=None):
        req = self.request
        scan_id = req.query_params.get('scan_id')
        if scan_id:
            tech = Email.objects.filter(
                emails__in=ScanHistory.objects.filter(id=scan_id))
            serializer = EmailSerializer(tech, many=True)
            return Response({"emails": serializer.data})


class ListPorts(APIView):
    def get(self, request, format=None):
        req = self.request
        scan_id = req.query_params.get('scan_id')
        ip_address = req.query_params.get('ip_address')
        if ip_address and scan_id:
            port = Port.objects.filter(
                ports__address=ip_address).filter(
                ports__in=IpAddress.objects.filter(
                    ip_addresses__in=Subdomain.objects.filter(
                        scan_history__id=scan_id))).distinct()
            serializer = PortSerializer(port, many=True)
            return Response({"ports": serializer.data})
        elif scan_id:
            port = Port.objects.filter(
                ports__in=IpAddress.objects.filter(
                    ip_addresses__in=Subdomain.objects.filter(
                        scan_history__id=scan_id))).distinct()
            serializer = PortSerializer(port, many=True)
            return Response({"ports": serializer.data})
        else:
            port = Port.objects.filter(
                ports__in=IpAddress.objects.filter(
                    ip_addresses__in=Subdomain.objects.all())).distinct()
            serializer = PortSerializer(port, many=True)
            return Response({"ports": serializer.data})


class ListSubdomains(APIView):
    def get(self, request, format=None):
        req = self.request
        scan_id = req.query_params.get('scan_id')
        ip_address = req.query_params.get('ip_address')
        port = req.query_params.get('port')
        tech = req.query_params.get('tech')
        if scan_id and ip_address:
            subdomain = Subdomain.objects.filter(
                ip_addresses__address=ip_address).filter(
                scan_history__id=scan_id)
            serializer = SubdomainSerializer(subdomain, many=True)
            return Response({"subdomains": serializer.data})
        elif scan_id and tech:
            subdomain = Subdomain.objects.filter(
                technologies__name=tech).filter(
                scan_history__id=scan_id)
            serializer = SubdomainSerializer(subdomain, many=True)
            return Response({"subdomains": serializer.data})
        elif scan_id and port:
            subdomain = Subdomain.objects.filter(
                ip_addresses__in=IpAddress.objects.filter(
                    ports__in=Port.objects.filter(
                        number=port))).filter(
                scan_history=scan_id)
            serializer = SubdomainSerializer(subdomain, many=True)
            return Response({"subdomains": serializer.data})


class ListOsintUsers(APIView):
    def get(self, request, format=None):
        req = self.request
        scan_id = req.query_params.get('scan_id')
        if scan_id:
            documents = MetaFinderDocument.objects.filter(scan_history__id=scan_id).exclude(author__isnull=True).values('author').distinct()
            serializer = MetafinderUserSerializer(documents, many=True)
            return Response({"users": serializer.data})


class ListMetadata(APIView):
    def get(self, request, format=None):
        req = self.request
        scan_id = req.query_params.get('scan_id')
        if scan_id:
            documents = MetaFinderDocument.objects.filter(scan_history__id=scan_id).distinct()
            serializer = MetafinderDocumentSerializer(documents, many=True)
            return Response({"metadata": serializer.data})


class ListIPs(APIView):
    def get(self, request, format=None):
        req = self.request
        scan_id = req.query_params.get('scan_id')
        port = req.query_params.get('port')
        if scan_id and port:
            ips = IpAddress.objects.filter(
                ip_addresses__in=Subdomain.objects.filter(
                    scan_history__id=scan_id)).filter(
                ports__in=Port.objects.filter(
                    number=port)).distinct()
            serializer = IpSerializer(ips, many=True)
            return Response({"ips": serializer.data})
        elif scan_id:
            ips = IpAddress.objects.filter(
                ip_addresses__in=Subdomain.objects.filter(
                    scan_history__id=scan_id)).distinct()
            serializer = IpSerializer(ips, many=True)
            return Response({"ips": serializer.data})
        else:
            ips = IpAddress.objects.filter(
                ip_addresses__in=Subdomain.objects.all()).distinct()
            serializer = IpSerializer(ips, many=True)
            return Response({"ips": serializer.data})


class IpAddressViewSet(viewsets.ModelViewSet):
    queryset = Subdomain.objects.none()
    serializer_class = IpSubdomainSerializer

    def get_queryset(self):
        req = self.request
        scan_id = req.query_params.get('scan_id')

        if scan_id:
            self.queryset = Subdomain.objects.filter(
                scan_history__id=scan_id).exclude(
                ip_addresses__isnull=True).distinct()
        else:
            self.serializer_class = IpSerializer
            self.queryset = Ip.objects.all()
        return self.queryset

    def paginate_queryset(self, queryset, view=None):
        if 'no_page' in self.request.query_params:
            return None
        return self.paginator.paginate_queryset(
            queryset, self.request, view=self)


class ListSubdomainsViewSet(viewsets.ModelViewSet):
    queryset = Subdomain.objects.none()
    serializer_class = SubdomainSerializer

    def get_queryset(self):
        req = self.request
        scan_id = req.query_params.get('scan_id')
        if scan_id:
            if 'only_screenshot' in self.request.query_params:
                return Subdomain.objects.filter(
                    scan_history__id=scan_id).exclude(
                    screenshot_path__isnull=True)
            return Subdomain.objects.filter(scan_history=scan_id)

    def paginate_queryset(self, queryset, view=None):
        if 'no_page' in self.request.query_params:
            return None
        return self.paginator.paginate_queryset(
            queryset, self.request, view=self)


class SubdomainChangesViewSet(viewsets.ModelViewSet):
    '''
        This viewset will return the Subdomain changes
        To get the new subdomains, we will look for ScanHistory with
        subdomain_discovery = True and the status of the last scan has to be
        successful and calculate difference
    '''
    queryset = Subdomain.objects.none()
    serializer_class = SubdomainChangesSerializer

    def get_queryset(self):
        req = self.request
        scan_id = req.query_params.get('scan_id')
        changes = req.query_params.get('changes')
        domain_id = ScanHistory.objects.filter(id=scan_id)[0].domain.id
        scan_history = ScanHistory.objects.filter(
            domain=domain_id).filter(
            subdomain_discovery=True).filter(
            id__lte=scan_id).filter(
                scan_status=2)
        if scan_history.count() > 1:
            last_scan = scan_history.order_by('-start_scan_date')[1]
            scanned_host_q1 = Subdomain.objects.filter(
                scan_history__id=scan_id).values('name')
            scanned_host_q2 = Subdomain.objects.filter(
                scan_history__id=last_scan.id).values('name')
            added_subdomain = scanned_host_q1.difference(scanned_host_q2)
            removed_subdomains = scanned_host_q2.difference(scanned_host_q1)
            if changes == 'added':
                return Subdomain.objects.filter(
                    scan_history=scan_id).filter(
                    name__in=added_subdomain).annotate(
                    change=Value(
                        'added',
                        output_field=CharField()))
            elif changes == 'removed':
                return Subdomain.objects.filter(
                    scan_history=last_scan).filter(
                    name__in=removed_subdomains).annotate(
                    change=Value(
                        'removed',
                        output_field=CharField()))
            else:
                added_subdomain = Subdomain.objects.filter(
                    scan_history=scan_id).filter(
                    name__in=added_subdomain).annotate(
                    change=Value(
                        'added',
                        output_field=CharField()))
                removed_subdomains = Subdomain.objects.filter(
                    scan_history=last_scan).filter(
                    name__in=removed_subdomains).annotate(
                    change=Value(
                        'removed',
                        output_field=CharField()))
                changes = added_subdomain.union(removed_subdomains)
                return changes
        return self.queryset

    def paginate_queryset(self, queryset, view=None):
        if 'no_page' in self.request.query_params:
            return None
        return self.paginator.paginate_queryset(
            queryset, self.request, view=self)


class EndPointChangesViewSet(viewsets.ModelViewSet):
    '''
        This viewset will return the EndPoint changes
    '''
    queryset = EndPoint.objects.none()
    serializer_class = EndPointChangesSerializer

    def get_queryset(self):
        req = self.request
        scan_id = req.query_params.get('scan_id')
        changes = req.query_params.get('changes')

        domain_id = ScanHistory.objects.filter(id=scan_id)[0].domain.id
        scan_history = ScanHistory.objects.filter(
            domain=domain_id).filter(
            fetch_url=True).filter(
            id__lte=scan_id).filter(
                scan_status=2)
        if scan_history.count() > 1:
            last_scan = scan_history.order_by('-start_scan_date')[1]
            scanned_host_q1 = EndPoint.objects.filter(
                scan_history__id=scan_id).values('http_url')
            scanned_host_q2 = EndPoint.objects.filter(
                scan_history__id=last_scan.id).values('http_url')
            added_endpoints = scanned_host_q1.difference(scanned_host_q2)
            removed_endpoints = scanned_host_q2.difference(scanned_host_q1)
            if changes == 'added':
                return EndPoint.objects.filter(
                    scan_history=scan_id).filter(
                    http_url__in=added_endpoints).annotate(
                    change=Value(
                        'added',
                        output_field=CharField()))
            elif changes == 'removed':
                return EndPoint.objects.filter(
                    scan_history=last_scan).filter(
                    http_url__in=removed_endpoints).annotate(
                    change=Value(
                        'removed',
                        output_field=CharField()))
            else:
                added_endpoints = EndPoint.objects.filter(
                    scan_history=scan_id).filter(
                    http_url__in=added_endpoints).annotate(
                    change=Value(
                        'added',
                        output_field=CharField()))
                removed_endpoints = EndPoint.objects.filter(
                    scan_history=last_scan).filter(
                    http_url__in=removed_endpoints).annotate(
                    change=Value(
                        'removed',
                        output_field=CharField()))
                changes = added_endpoints.union(removed_endpoints)
                return changes
        return self.queryset

    def paginate_queryset(self, queryset, view=None):
        if 'no_page' in self.request.query_params:
            return None
        return self.paginator.paginate_queryset(
            queryset, self.request, view=self)


class InterestingSubdomainViewSet(viewsets.ModelViewSet):
    queryset = Subdomain.objects.none()
    serializer_class = SubdomainSerializer

    def get_queryset(self):
        req = self.request
        scan_id = req.query_params.get('scan_id')
        target_id = req.query_params.get('target_id')
        if 'only_subdomains' in self.request.query_params:
            self.serializer_class = InterestingSubdomainSerializer
        if scan_id:
            return get_interesting_subdomains(scan_history=scan_id)
        elif target_id:
            return get_interesting_subdomains(target=target_id)
        else:
            return get_interesting_subdomains()

    def paginate_queryset(self, queryset, view=None):
        if 'no_page' in self.request.query_params:
            return None
        return self.paginator.paginate_queryset(
            queryset, self.request, view=self)


class InterestingEndpointViewSet(viewsets.ModelViewSet):
    queryset = EndPoint.objects.none()
    serializer_class = EndpointSerializer

    def get_queryset(self):
        req = self.request
        scan_id = req.query_params.get('scan_id')
        target_id = req.query_params.get('target_id')
        if 'only_endpoints' in self.request.query_params:
            self.serializer_class = InterestingEndPointSerializer
        if scan_id:
            return get_interesting_endpoint(scan_history=scan_id)
        elif target_id:
            return get_interesting_endpoint(target=target_id)
        else:
            return get_interesting_endpoint()

    def paginate_queryset(self, queryset, view=None):
        if 'no_page' in self.request.query_params:
            return None
        return self.paginator.paginate_queryset(
            queryset, self.request, view=self)


class SubdomainViewset(viewsets.ModelViewSet):
    queryset = Subdomain.objects.none()
    serializer_class = SubdomainSerializer

    def get_queryset(self):
        req = self.request
        scan_id = req.query_params.get('scan_id')

        url_query = req.query_params.get('query_param')
        if url_query:
            self.queryset = Subdomain.objects.filter(
                Q(target_domain__name=url_query)).distinct()
        elif scan_id:
            self.queryset = Subdomain.objects.filter(
                scan_history__id=scan_id).distinct()
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
            order_col = 'name'
        elif _order_col == '2':
            order_col = 'endpoint'
        elif _order_col == '3':
            order_col = 'vulnerability'
        elif _order_col == '4':
            order_col = 'http_status'
        elif _order_col == '5':
            order_col = 'page_title'
        elif _order_col == '6':
            order_col = 'ip_addresses'
        elif _order_col == '8':
            order_col = 'content_length'
        elif _order_col == '10':
            order_col = 'response_time'
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
                qs = Subdomain.objects.none()
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
            Q(name__icontains=search_value) |
            Q(cname__icontains=search_value) |
            Q(http_status__icontains=search_value) |
            Q(content_length__icontains=search_value) |
            Q(page_title__icontains=search_value) |
            Q(http_url__icontains=search_value) |
            Q(is_cdn__icontains=search_value) |
            Q(screenshot_path__icontains=search_value) |
            Q(http_header_path__icontains=search_value) |
            Q(technologies__name__icontains=search_value) |
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
            if 'name' in lookup_title:
                qs = self.queryset.filter(subdomain__icontains=lookup_content)
            elif 'cname' in lookup_title:
                qs = self.queryset.filter(cname__icontains=lookup_content)
            elif 'ip_addresses' in lookup_title or 'ip' in lookup_title:
                qs = self.queryset.filter(
                    ip_addresses__icontains=lookup_content)
            elif 'tech' in lookup_title or 'technology' in lookup_title or 'technologies' in lookup_title:
                qs = self.queryset.filter(
                    technologies__name__icontains=lookup_content)
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
                    qs = self.queryset.filter(is_cdn=True)
                elif lookup_content == 'false':
                    qs = self.queryset.filter(is_cdn=False)
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
            if 'name' in lookup_title:
                qs = self.queryset.exclude(subdomain__icontains=lookup_content)
            elif 'cname' in lookup_title:
                qs = self.queryset.exclude(cname__icontains=lookup_content)
            elif 'ip_addresses' in lookup_title or 'ip' in lookup_title:
                qs = self.queryset.exclude(
                    ip_addresses__icontains=lookup_content)
            elif 'tech' in lookup_title or 'technology' in lookup_title or 'technologies' in lookup_title:
                qs = self.queryset.exclude(
                    technologies__name__icontains=lookup_content)
            elif 'http_status' in lookup_title:
                try:
                    int_http_status = int(lookup_content)
                    qs = self.queryset.exclude(http_status=int_http_status)
                except Exception as e:
                    print(e)
            elif 'cdn' in lookup_title:
                if lookup_content == 'true':
                    qs = self.queryset.exclude(is_cdn=True)
                elif lookup_content == 'false':
                    qs = self.queryset.exclude(is_cdn=False)
            elif 'status' in lookup_title:
                if lookup_content == 'open':
                    qs = self.queryset.exclude(checked=False)
                elif lookup_content == 'closed':
                    qs = self.queryset.exclude(checked=True)
        return qs


class EndPointViewSet(viewsets.ModelViewSet):
    queryset = EndPoint.objects.all()
    serializer_class = EndpointSerializer

    def get_queryset(self):
        req = self.request
        scan_history = req.query_params.get(
            'scan_history') if 'scan_history' in req.query_params else None
        gf_tag = req.query_params.get(
            'gf_tag') if 'gf_tag' in req.query_params else None
        url_query = req.query_params.get(
            'query_param') if 'query_param' in req.query_params else None
        if url_query:
            if url_query.isnumeric():
                self.queryset = EndPoint.objects.filter(
                    Q(
                        scan_history__domain__name=url_query) | Q(
                        http_url=url_query) | Q(
                        id=url_query))
            else:
                self.queryset = EndPoint.objects.filter(
                    Q(scan_history__domain__name=url_query) | Q(http_url=url_query))
        elif scan_history:
            self.queryset = EndPoint.objects.filter(
                scan_history__id=scan_history)

        '''
        look for tags
        '''
        if gf_tag and scan_history:
            self.queryset = EndPoint.objects.filter(
                scan_history__id=scan_history).filter(
                matched_gf_patterns__icontains=gf_tag)
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
            order_col = 'page_title'
        elif _order_col == '3':
            order_col = 'matched_gf_patterns'
        elif _order_col == '4':
            order_col = 'content_type'
        elif _order_col == '5':
            order_col = 'content_length'
        elif _order_col == '6':
            order_col = 'technologies'
        elif _order_col == '7':
            order_col = 'webserver'
        elif _order_col == '8':
            order_col = 'response_time'
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
                qs = Subdomain.objects.none()
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
                qs = self.queryset.filter(
                    content_type__icontains=lookup_content)
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
                qs = self.queryset.exclude(
                    content_type__icontains=lookup_content)
        return qs


class VulnerabilityViewSet(viewsets.ModelViewSet):
    queryset = Vulnerability.objects.all().order_by('-discovered_date')
    serializer_class = VulnerabilitySerializer

    def get_queryset(self):
        req = self.request
        vulnerability_of = req.query_params.get('scan_history')
        url_query = req.query_params.get('query_param')
        if url_query:
            if url_query.isnumeric():
                self.queryset = Vulnerability.objects.filter(
                    Q(
                        scan_history__domain__name=url_query) | Q(
                        name=url_query) | Q(
                        id=url_query))
            else:
                self.queryset = Vulnerability.objects.filter(
                    Q(scan_history__domain__name=url_query) | Q(name=url_query))
        elif vulnerability_of:
            self.queryset = Vulnerability.objects.filter(
                scan_history__id=vulnerability_of)
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
                qs = Vulnerability.objects.none()
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
            Q(http_url__icontains=search_value) |
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

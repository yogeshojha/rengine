import json

from django.db.models import Q
from django.db.models import CharField, Value, Count
from django.core import serializers
from rest_framework import viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view, action
from rest_framework import generics

from reNgine.common_func import *

from .serializers import *
from scanEngine.models import *
from startScan.models import *
from targetApp.models import *
from recon_note.models import *

from reNgine.common_func import is_safe_path

class VulnerabilityReport(APIView):
    def get(self, request):
        req = self.request
        vulnerability_id = req.query_params.get('vulnerability_id')
        return Response({"status": send_hackerone_report(vulnerability_id)})

class GetFileContents(APIView):
    def get(self, request, format=None):
        req = self.request
        name = req.query_params.get('name')

        if 'nuclei_config' in req.query_params:
            path = "/root/.config/nuclei/config.yaml"
            if not os.path.exists(path):
                os.system('touch {}'.format(path))
            f = open(path, "r")
            return Response({'content': f.read()})

        if 'subfinder_config' in req.query_params:
            path = "/root/.config/subfinder/config.yaml"
            if not os.path.exists(path):
                os.system('touch {}'.format(path))
            f = open(path, "r")
            return Response({'content': f.read()})

        if 'naabu_config' in req.query_params:
            path = "/root/.config/naabu/naabu.conf"
            if not os.path.exists(path):
                os.system('touch {}'.format(path))
            f = open(path, "r")
            return Response({'content': f.read()})

        if 'amass_config' in req.query_params:
            path = "/root/.config/amass.ini"
            if not os.path.exists(path):
                os.system('touch {}'.format(path))
            f = open(path, "r")
            return Response({'content': f.read()})

        if 'gf_pattern' in req.query_params:
            basedir = '/root/.gf'
            path = '/root/.gf/{}.json'.format(name)
            if is_safe_path(basedir, path) and os.path.exists(path):
                content = open(path, "r").read()
            else:
                content = "Invalid path!"
            return Response({'content': content})


        if 'nuclei_template' in req.query_params:
            safe_dir = '/root/nuclei-templates'
            path = '/root/nuclei-templates/{}'.format(name)
            if is_safe_path(safe_dir, path) and os.path.exists(path):
                content = open(path.format(name), "r").read()
            else:
                content = 'Invalid Path!'
            return Response({'content': content})

        return Response({'content': "ping-pong"})


class ListTodoNotes(APIView):
    def get(self, request, format=None):
        req = self.request
        notes = TodoNote.objects.all().order_by('-id')
        scan_id = req.query_params.get('scan_id')
        target_id = req.query_params.get('target_id')
        todo_id = req.query_params.get('todo_id')
        subdomain_id = req.query_params.get('subdomain_id')
        if target_id:
            notes = notes.filter(scan_history__domain__id=target_id)
        elif scan_id:
            notes = notes.filter(scan_history__id=scan_id)
        if todo_id:
            notes = notes.filter(id=todo_id)
        if subdomain_id:
            notes = notes.filter(subdomain__id=subdomain_id)
        notes = ReconNoteSerializer(notes, many=True)
        return Response({'notes': notes.data})


class ListScanHistory(APIView):
    def get(self, request, format=None):
        req = self.request
        scan_history = ScanHistory.objects.all().order_by('-start_scan_date')
        scan_history = ScanHistorySerializer(scan_history, many=True)
        return Response({'scan_histories': scan_history.data})


class ListEngines(APIView):
    def get(self, request, format=None):
        req = self.request
        engine = EngineType.objects.all()
        engine_serializer = EngineSerializer(engine, many=True)
        return Response({'engines': engine_serializer.data})


class ListOrganizations(APIView):
    def get(self, request, format=None):
        req = self.request
        organizations = Organization.objects.all()
        organization_serializer = OrganizationSerializer(organizations, many=True)
        return Response({'organizations': organization_serializer.data})


class ListTargetsInOrganization(APIView):
    def get(self, request, format=None):
        req = self.request
        organization_id = req.query_params.get('organization_id')
        organization = Organization.objects.filter(id=organization_id)
        targets = Domain.objects.filter(domains__in=organization)
        organization_serializer = OrganizationSerializer(organization, many=True)
        targets_serializer = OrganizationTargetsSerializer(targets, many=True)
        return Response({'organization': organization_serializer.data, 'domains': targets_serializer.data})


class ListTargetsWithoutOrganization(APIView):
    def get(self, request, format=None):
        req = self.request
        targets = Domain.objects.exclude(domains__in=Organization.objects.all())
        targets_serializer = OrganizationTargetsSerializer(targets, many=True)
        return Response({'domains': targets_serializer.data})


class ListVulnerability(APIView):
    def get(self, request, format=None):
        req = self.request
        scan_id = req.query_params.get('scan_id')
        severity = req.query_params.get('severity')
        subdomain_name = req.query_params.get('subdomain_name')

        if scan_id:
            vulnerability = Vulnerability.objects.filter(scan_history__id=scan_id)
        else:
            vulnerability = Vulnerability.objects.all()

        if severity:
            vulnerability = vulnerability.filter(severity=severity)

        if subdomain_name:
            vulnerability = vulnerability.filter(subdomain__name=subdomain_name)

        vulnerability_serializer = VulnerabilitySerializer(vulnerability, many=True)
        return Response({'vulnerabilities': vulnerability_serializer.data})


class ListEndpoints(APIView):
    def get(self, request, format=None):
        req = self.request
        scan_id = req.query_params.get('scan_id')
        subdomain_name = req.query_params.get('subdomain_name')
        pattern = req.query_params.get('pattern')

        if scan_id:
            endpoints = EndPoint.objects.filter(scan_history__id=scan_id)
        else:
            endpoints = EndPoint.objects.all()

        if subdomain_name:
            endpoints = endpoints.filter(subdomain__name=subdomain_name)

        if pattern:
            endpoints = endpoints.filter(matched_gf_patterns__icontains=pattern)

        if 'only_urls' in req.query_params:
            endpoints_serializer = EndpointOnlyURLsSerializer(endpoints, many=True)

        else:
            endpoints_serializer = EndpointSerializer(endpoints, many=True)

        return Response({'endpoints': endpoints_serializer.data})


class VisualiseData(APIView):
    def get(self, request, format=None):
        req = self.request
        scan_id = req.query_params.get('scan_id')
        if scan_id:
            mitch_data = ScanHistory.objects.filter(id=scan_id)
            serializer = VisualiseDataSerializer(mitch_data, many=True)
            return Response(serializer.data)
        else:
            return Response()


class ListTechnology(APIView):
    def get(self, request, format=None):
        req = self.request
        scan_id = req.query_params.get('scan_id')
        target_id = req.query_params.get('target_id')

        if target_id:
            tech = Technology.objects.filter(
                technologies__in=Subdomain.objects.filter(
                    target_domain__id=target_id)).annotate(
                count=Count('name')).order_by('-count')
            serializer = TechnologyCountSerializer(tech, many=True)
            return Response({"technologies": serializer.data})
        elif scan_id:
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


class ListDorkTypes(APIView):
    def get(self, request, format=None):
        req = self.request
        scan_id = req.query_params.get('scan_id')
        if scan_id:
            dork = Dork.objects.filter(
                dorks__in=ScanHistory.objects.filter(id=scan_id)
            ).values('type').annotate(count=Count('type')).order_by('-count')
            serializer = DorkCountSerializer(dork, many=True)
            return Response({"dorks": serializer.data})
        else:
            dork = Dork.objects.filter(
                dorks__in=ScanHistory.objects.all()
            ).values('type').annotate(count=Count('type')).order_by('-count')
            serializer = DorkCountSerializer(dork, many=True)
            return Response({"dorks": serializer.data})


class ListEmails(APIView):
    def get(self, request, format=None):
        req = self.request
        scan_id = req.query_params.get('scan_id')
        if scan_id:
            email = Email.objects.filter(
                emails__in=ScanHistory.objects.filter(id=scan_id)).order_by('password')
            serializer = EmailSerializer(email, many=True)
            return Response({"emails": serializer.data})


class ListDorks(APIView):
    def get(self, request, format=None):
        req = self.request
        scan_id = req.query_params.get('scan_id')
        type = req.query_params.get('type')
        if scan_id:
            dork = Dork.objects.filter(
                dorks__in=ScanHistory.objects.filter(id=scan_id))
        else:
            dork = Dork.objects.filter(
                dorks__in=ScanHistory.objects.all())
        if scan_id and type:
            dork = dork.filter(type=type)
        serializer = DorkSerializer(dork, many=True)
        return Response({"dorks": serializer.data})


class ListEmployees(APIView):
    def get(self, request, format=None):
        req = self.request
        scan_id = req.query_params.get('scan_id')
        if scan_id:
            employee = Employee.objects.filter(
                employees__in=ScanHistory.objects.filter(id=scan_id))
            serializer = EmployeeSerializer(employee, many=True)
            return Response({"employees": serializer.data})


class ListPorts(APIView):
    def get(self, request, format=None):
        req = self.request
        scan_id = req.query_params.get('scan_id')
        target_id = req.query_params.get('target_id')
        ip_address = req.query_params.get('ip_address')

        if target_id:
            port = Port.objects.filter(
                ports__in=IpAddress.objects.filter(
                    ip_addresses__in=Subdomain.objects.filter(
                        target_domain__id=target_id))).distinct()
        elif scan_id:
            port = Port.objects.filter(
                ports__in=IpAddress.objects.filter(
                    ip_addresses__in=Subdomain.objects.filter(
                        scan_history__id=scan_id))).distinct()
        else:
            port = Port.objects.filter(
                ports__in=IpAddress.objects.filter(
                    ip_addresses__in=Subdomain.objects.all())).distinct()

        if ip_address:
            port = port.filter(ports__address=ip_address).distinct()

        serializer = PortSerializer(port, many=True)
        return Response({"ports": serializer.data})


class ListSubdomains(APIView):
    def get(self, request, format=None):
        req = self.request
        scan_id = req.query_params.get('scan_id')
        target_id = req.query_params.get('target_id')
        ip_address = req.query_params.get('ip_address')
        port = req.query_params.get('port')
        tech = req.query_params.get('tech')

        if scan_id:
            subdomain_query = Subdomain.objects.filter(scan_history__id=scan_id).distinct('name')
        elif target_id:
            subdomain_query = Subdomain.objects.filter(target_domain__id=target_id).distinct('name')
        else:
            subdomain_query = Subdomain.objects.all().distinct('name')

        if ip_address:
            subdomain_query = subdomain_query.filter(ip_addresses__address=ip_address)

        if tech:
            subdomain_query = subdomain_query.filter(technologies__name=tech)

        if port:
            subdomain_query = subdomain_query.filter(
                ip_addresses__in=IpAddress.objects.filter(
                    ports__in=Port.objects.filter(
                        number=port)))

        if 'only_important' in req.query_params:
	           subdomain_query = subdomain_query.filter(is_important=True)


        if 'no_lookup_interesting' in req.query_params:
            serializer = OnlySubdomainNameSerializer(subdomain_query, many=True)
        else:
            serializer = SubdomainSerializer(subdomain_query, many=True)
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
        target_id = req.query_params.get('target_id')

        port = req.query_params.get('port')

        if target_id:
            ips = IpAddress.objects.filter(
                ip_addresses__in=Subdomain.objects.filter(
                    target_domain__id=target_id)).distinct()
        elif scan_id:
            ips = IpAddress.objects.filter(
                ip_addresses__in=Subdomain.objects.filter(
                    scan_history__id=scan_id)).distinct()
        else:
            ips = IpAddress.objects.filter(
                ip_addresses__in=Subdomain.objects.all()).distinct()

        if port:
            ips = ips.filter(
                ports__in=Port.objects.filter(
                    number=port)).distinct()


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


class SubdomainsViewSet(viewsets.ModelViewSet):
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
            queryset = get_interesting_subdomains(target=target_id)
            return queryset
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


class SubdomainDatatableViewSet(viewsets.ModelViewSet):
    queryset = Subdomain.objects.none()
    serializer_class = SubdomainSerializer

    def get_queryset(self):
        req = self.request
        scan_id = req.query_params.get('scan_id')

        target_id = req.query_params.get('target_id')

        url_query = req.query_params.get('query_param')

        ip_address = req.query_params.get('ip_address')

        if target_id:
            self.queryset = Subdomain.objects.filter(
                target_domain__id=target_id).distinct()
        elif url_query:
            self.queryset = Subdomain.objects.filter(
                Q(target_domain__name=url_query)).distinct()
        elif scan_id:
            self.queryset = Subdomain.objects.filter(
                scan_history__id=scan_id).distinct()
        else:
            self.queryset = Subdomain.objects.distinct()

        if 'only_diretory' in req.query_params:
            self.queryset = self.queryset.exclude(directory_json__isnull=True)

        if ip_address:
            print(ip_address)
            self.queryset = self.queryset.filter(ip_addresses__address__icontains=ip_address)

        return self.queryset

    def filter_queryset(self, qs):
        qs = self.queryset.filter()
        search_value = self.request.GET.get(u'search[value]', None)
        _order_col = self.request.GET.get(u'order[0][column]', None)
        _order_direction = self.request.GET.get(u'order[0][dir]', None)
        order_col = 'content_length'
        print(_order_col)
        if _order_col == '0':
            order_col = 'checked'
        elif _order_col == '1':
            order_col = 'name'
        elif _order_col == '4':
            order_col = 'http_status'
        elif _order_col == '5':
            order_col = 'page_title'
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
            Q(name__icontains=search_value) |
            Q(cname__icontains=search_value) |
            Q(http_status__icontains=search_value) |
            Q(page_title__icontains=search_value) |
            Q(http_url__icontains=search_value) |
            Q(technologies__name__icontains=search_value) |
            Q(webserver__icontains=search_value) |
            Q(ip_addresses__address__icontains=search_value) |
            Q(ip_addresses__ports__number__icontains=search_value) |
            Q(ip_addresses__ports__service_name__icontains=search_value) |
            Q(ip_addresses__ports__description__icontains=search_value)
        )

        return qs

    def special_lookup(self, search_value):
        qs = self.queryset.filter()
        print(search_value)
        if '=' in search_value:
            search_param = search_value.split("=")
            lookup_title = search_param[0].lower().strip()
            lookup_content = search_param[1].lower().strip()
            if 'name' in lookup_title:
                qs = self.queryset.filter(name__icontains=lookup_content)
            elif 'page_title' in lookup_title:
                qs = self.queryset.filter(page_title__icontains=lookup_content)
            elif 'http_url' in lookup_title:
                qs = self.queryset.filter(http_url__icontains=lookup_content)
            elif 'content_type' in lookup_title:
                qs = self.queryset.filter(content_type__icontains=lookup_content)
            elif 'cname' in lookup_title:
                qs = self.queryset.filter(cname__icontains=lookup_content)
            elif 'webserver' in lookup_title:
                qs = self.queryset.filter(webserver__icontains=lookup_content)
            elif 'ip_addresses' in lookup_title:
                qs = self.queryset.filter(
                    ip_addresses__address__icontains=lookup_content)
            elif 'is_important' in lookup_title:
                if 'true' in lookup_content.lower():
                    qs = self.queryset.filter(is_important=True)
                else:
                    qs = self.queryset.filter(is_important=False)
            elif 'port' in lookup_title:
                qs = self.queryset.filter(
                    ip_addresses__ports__number__icontains=lookup_content
                    ) | self.queryset.filter(
                    ip_addresses__ports__service_name__icontains=lookup_content
                    ) | self.queryset.filter(ip_addresses__ports__description__icontains=lookup_content)
            elif 'technology' in lookup_title:
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
                qs = self.queryset.exclude(name__icontains=lookup_content)
            elif 'page_title' in lookup_title:
                qs = self.queryset.exclude(page_title__icontains=lookup_content)
            elif 'http_url' in lookup_title:
                qs = self.queryset.exclude(http_url__icontains=lookup_content)
            elif 'content_type' in lookup_title:
                qs = self.queryset.exclude(content_type__icontains=lookup_content)
            elif 'cname' in lookup_title:
                qs = self.queryset.exclude(cname__icontains=lookup_content)
            elif 'webserver' in lookup_title:
                qs = self.queryset.exclude(webserver__icontains=lookup_content)
            elif 'ip_addresses' in lookup_title:
                qs = self.queryset.exclude(
                    ip_addresses__address__icontains=lookup_content)
            elif 'port' in lookup_title:
                qs = self.queryset.exclude(
                    ip_addresses__ports__number__icontains=lookup_content
                    ) | self.queryset.exclude(
                    ip_addresses__ports__service_name__icontains=lookup_content
                    ) | self.queryset.exclude(ip_addresses__ports__description__icontains=lookup_content)
            elif 'technology' in lookup_title:
                qs = self.queryset.exclude(
                    technologies__name__icontains=lookup_content)
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

        return qs


class EndPointViewSet(viewsets.ModelViewSet):
    queryset = EndPoint.objects.none()
    serializer_class = EndpointSerializer

    def get_queryset(self):
        req = self.request
        scan_id = req.query_params.get('scan_history')

        target_id = req.query_params.get('target_id')

        url_query = req.query_params.get('query_param')

        gf_tag = req.query_params.get(
            'gf_tag') if 'gf_tag' in req.query_params else None

        if scan_id:
            self.queryset = EndPoint.objects.filter(
                scan_history__id=scan_id
            ).distinct()

        elif target_id:
            self.queryset = EndPoint.objects.filter(
                target_domain__id=target_id).distinct()
        else:
            self.queryset = EndPoint.objects.distinct()

        if url_query:
            self.queryset = EndPoint.objects.filter(
                Q(target_domain__name=url_query)).distinct()

        if gf_tag:
            self.queryset = self.queryset.filter(matched_gf_patterns__icontains=gf_tag)

        return self.queryset

    def filter_queryset(self, qs):
        qs = self.queryset.filter()
        search_value = self.request.GET.get(u'search[value]', None)
        _order_col = self.request.GET.get(u'order[0][column]', None)
        _order_direction = self.request.GET.get(u'order[0][dir]', None)
        order_col = 'content_length'
        if _order_col == '1':
            order_col = 'http_url'
        elif _order_col == '2':
            order_col = 'http_status'
        elif _order_col == '3':
            order_col = 'page_title'
        elif _order_col == '4':
            order_col = 'matched_gf_patterns'
        elif _order_col == '5':
            order_col = 'content_type'
        elif _order_col == '6':
            order_col = 'content_length'
        elif _order_col == '7':
            order_col = 'technologies'
        elif _order_col == '8':
            order_col = 'webserver'
        elif _order_col == '9':
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
            Q(page_title__icontains=search_value) |
            Q(http_status__icontains=search_value) |
            Q(content_type__icontains=search_value) |
            Q(webserver__icontains=search_value) |
            Q(technologies__name__icontains=search_value) |
            Q(content_type__icontains=search_value) |
            Q(matched_gf_patterns__icontains=search_value))

        return qs

    def special_lookup(self, search_value):
        qs = self.queryset.filter()
        print(search_value)
        if '=' in search_value:
            search_param = search_value.split("=")
            lookup_title = search_param[0].lower().strip()
            lookup_content = search_param[1].lower().strip()
            if 'http_url' in lookup_title:
                qs = self.queryset.filter(http_url__icontains=lookup_content)
            elif 'page_title' in lookup_title:
                qs = self.queryset.filter(page_title__icontains=lookup_content)
            elif 'content_type' in lookup_title:
                qs = self.queryset.filter(content_type__icontains=lookup_content)
            elif 'webserver' in lookup_title:
                qs = self.queryset.filter(webserver__icontains=lookup_content)
            elif 'technology' in lookup_title:
                qs = self.queryset.filter(
                    technologies__name__icontains=lookup_content)
            elif 'gf_pattern' in lookup_title:
                qs = self.queryset.filter(
                    matched_gf_patterns__icontains=lookup_content)
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
            if 'http_url' in lookup_title:
                qs = self.queryset.exclude(http_url__icontains=lookup_content)
            elif 'page_title' in lookup_title:
                qs = self.queryset.exclude(page_title__icontains=lookup_content)
            elif 'content_type' in lookup_title:
                qs = self.queryset.exclude(content_type__icontains=lookup_content)
            elif 'webserver' in lookup_title:
                qs = self.queryset.exclude(webserver__icontains=lookup_content)
            elif 'technology' in lookup_title:
                qs = self.queryset.exclude(
                technologies__name__icontains=lookup_content)
            elif 'gf_pattern' in lookup_title:
                qs = self.queryset.exclude(
                matched_gf_patterns__icontains=lookup_content)
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
        return qs


class VulnerabilityViewSet(viewsets.ModelViewSet):
    queryset = Vulnerability.objects.none()
    serializer_class = VulnerabilitySerializer

    def get_queryset(self):
        req = self.request
        scan_id = req.query_params.get('scan_history')

        target_id = req.query_params.get('target_id')

        domain = req.query_params.get('domain')

        vulnerability_name = req.query_params.get('vulnerability_name')

        if scan_id:
            self.queryset = Vulnerability.objects.filter(
                scan_history__id=scan_id).distinct()

        elif target_id:
            self.queryset = Vulnerability.objects.filter(
                target_domain__id=target_id).distinct()

        elif domain:
            self.queryset = Vulnerability.objects.filter(
                Q(target_domain__name=domain)).distinct()

        elif vulnerability_name:
            self.queryset = Vulnerability.objects.filter(
                Q(name=vulnerability_name)).distinct()

        else:
            self.queryset = Vulnerability.objects.distinct()


        return self.queryset

    def filter_queryset(self, qs):
        qs = self.queryset.filter()
        search_value = self.request.GET.get(u'search[value]', None)
        _order_col = self.request.GET.get(u'order[0][column]', None)
        _order_direction = self.request.GET.get(u'order[0][dir]', None)
        order_col = 'severity'
        print(_order_col)
        if _order_col == '0' or _order_col == '5':
            order_col = 'open_status'
        elif _order_col == '1':
            order_col = 'name'
        elif _order_col == '2':
            order_col = 'severity'
        elif _order_col == '3':
            order_col = 'http_url'
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
            Q(name__icontains=search_value) |
            Q(severity__icontains=search_value) |
            Q(description__icontains=search_value) |
            Q(extracted_results__icontains=search_value) |
            Q(template_used__icontains=search_value) |
            Q(tags__icontains=search_value) |
            Q(matcher_name__icontains=search_value))
        return qs

    def special_lookup(self, search_value):
        qs = self.queryset.filter()
        if '=' in search_value:
            search_param = search_value.split("=")
            lookup_title = search_param[0].lower().strip()
            lookup_content = search_param[1].lower().strip()
            if 'severity' in lookup_title:
                print(lookup_content)
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
            elif 'name' in lookup_title:
                qs = self.queryset.filter(name__icontains=lookup_content)
            elif 'http_url' in lookup_title:
                qs = self.queryset.filter(http_url__icontains=lookup_content)
            elif 'tag' in lookup_title:
                qs = self.queryset.filter(tags__icontains=lookup_content)
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
            print(search_value)
            search_param = search_value.split("!")
            lookup_title = search_param[0].lower().strip()
            lookup_content = search_param[1].lower().strip()
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
                    qs = self.queryset.exclude(severity=severity_value)
            elif 'title' in lookup_title:
                qs = self.queryset.exclude(name__icontains=lookup_content)
            elif 'http_url' in lookup_title:
                qs = self.queryset.exclude(http_url__icontains=lookup_content)
            elif 'tag' in lookup_title:
                qs = self.queryset.exclude(tags__icontains=lookup_content)
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

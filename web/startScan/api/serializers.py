from rest_framework import serializers
from startScan.models import *
from reNgine.common_func import *

from django.db.models import F, JSONField, Value


class VisualisePortSerializer(serializers.ModelSerializer):

    description = serializers.SerializerMethodField('get_description')

    class Meta:
        model = Port
        fields = [
            'description'
        ]

    def get_description(self, port):
        return str(port.number) + "/" + port.service_name


class VisualiseIpSerializer(serializers.ModelSerializer):

    description = serializers.SerializerMethodField('get_description')
    children = serializers.SerializerMethodField('get_children')

    class Meta:
        model = IpAddress
        fields = [
            'description',
            'children'
        ]

    def get_description(self, Ip):
        return Ip.address

    def get_children(self, ip):
        port = Port.objects.filter(
            ports__in=IpAddress.objects.filter(
                address=ip))
        serializer = VisualisePortSerializer(port, many=True)
        return serializer.data


class VisualiseEndpointSerializer(serializers.ModelSerializer):

    description = serializers.SerializerMethodField('get_description')

    class Meta:
        model = EndPoint
        fields = [
            'description',
            'http_url'
        ]

    def get_description(self, endpoint):
        return endpoint.http_url


class VisualiseSubdomainSerializer(serializers.ModelSerializer):

    children = serializers.SerializerMethodField('get_children')
    description = serializers.SerializerMethodField('get_description')
    title = serializers.SerializerMethodField('get_title')

    class Meta:
        model = Subdomain
        fields = [
            'description',
            'children',
            'http_status',
            'title',
        ]

    def get_description(self, subdomain):
        return subdomain.name

    def get_title(self, subdomain):
        if get_interesting_subdomains(subdomain.scan_history.id).filter(name=subdomain.name).exists():
            return "Interesting"

    def get_children(self, subdomain_name):
        subdomain = Subdomain.objects.filter(
            scan_history=self.context.get('scan_history')).filter(
            name=subdomain_name)
        ips = IpAddress.objects.filter(ip_addresses__in=subdomain)
        ip_serializer = VisualiseIpSerializer(ips, many=True)

        endpoint = EndPoint.objects.filter(
            scan_history=self.context.get('scan_history')).filter(
            subdomain__name=subdomain_name)
        endpoint_serializer = VisualiseEndpointSerializer(endpoint, many=True)

        return_data = []
        if ip_serializer.data:
            return_data.append({'description': 'IPs', 'children': ip_serializer.data})
        if endpoint_serializer.data:
            return_data.append({'description': 'Endpoints', 'children': endpoint_serializer.data})
        return return_data


class VisualiseEmailSerializer(serializers.ModelSerializer):

    description = serializers.SerializerMethodField('get_description')

    class Meta:
        model = Email
        fields = [
            'description'
        ]

    def get_description(self, Email):
        return Email.address


class VisualiseDorkSerializer(serializers.ModelSerializer):

    title = serializers.SerializerMethodField('get_title')
    description = serializers.SerializerMethodField('get_description')
    http_url = serializers.SerializerMethodField('get_http_url')

    class Meta:
        model = Dork
        fields = [
            'title',
            'description',
            'http_url'
        ]

    def get_title(self, dork):
        return dork.type

    def get_description(self, dork):
        return dork.description

    def get_http_url(self, dork):
        return dork.url


class VisualiseEmployeeSerializer(serializers.ModelSerializer):

    description = serializers.SerializerMethodField('get_description')

    class Meta:
        model = Employee
        fields = [
            'description'
        ]

    def get_description(self, employee):
        if employee.designation:
            return employee.name + '--' + employee.designation
        return employee.name


class VisualiseDataSerializer(serializers.ModelSerializer):

    title = serializers.ReadOnlyField(default='Target')
    description = serializers.SerializerMethodField('get_description')
    children = serializers.SerializerMethodField('get_children')

    class Meta:
        model = ScanHistory
        fields = [
            'description',
            'title',
            'children',
        ]

    def get_description(self, scan_history):
        return scan_history.domain.name

    def get_children(self, history):
        scan_history = ScanHistory.objects.filter(id=history.id)

        subdomain = Subdomain.objects.filter(scan_history=history)
        subdomain_serializer = VisualiseSubdomainSerializer(
            subdomain, many=True, context={
                'scan_history': history})

        email = Email.objects.filter(emails__in=scan_history)
        email_serializer = VisualiseEmailSerializer(email, many=True)

        dork = Dork.objects.filter(dorks__in=scan_history)
        dork_serializer = VisualiseDorkSerializer(dork, many=True)

        employee = Employee.objects.filter(employees__in=scan_history)
        employee_serializer = VisualiseEmployeeSerializer(employee, many=True)

        metainfo = MetaFinderDocument.objects.filter(
            scan_history__id=history.id)

        return_data = []

        if subdomain_serializer.data:
            return_data.append({'description': 'Subdomains', 'children': subdomain_serializer.data})

        if email_serializer.data or employee_serializer.data or dork_serializer.data or metainfo:
            osint_data = []
            if email_serializer.data:
                osint_data.append({'description': 'Emails', 'children': email_serializer.data})
            if employee_serializer.data:
                osint_data.append({'description': 'Employees', 'children': employee_serializer.data})
            if dork_serializer.data:
                osint_data.append({'description': 'Dorks', 'children': dork_serializer.data})

            if metainfo:
                metainfo_data = []
                usernames = metainfo.annotate(
                    description=F('author')
                ).values('description').distinct().annotate(
                    children=Value(
                        [], output_field=JSONField())
                    ).filter(author__isnull=False)

                if usernames:
                    metainfo_data.append({'description': 'Usernames', 'children': usernames})

                software = metainfo.annotate(
                    description=F('producer')
                ).values('description').distinct().annotate(
                    children=Value(
                        [], output_field=JSONField())
                    ).filter(producer__isnull=False)

                if software:
                    metainfo_data.append({'description': 'Software', 'children': software})

                os = metainfo.annotate(
                    description=F('os')
                ).values('description').distinct().annotate(
                    children=Value(
                        [], output_field=JSONField())
                    ).filter(os__isnull=False)

                if os:
                    metainfo_data.append({'description': 'OS', 'children': os})

            if metainfo:
                osint_data.append({'description':'Metainfo', 'children': metainfo_data})

            return_data.append({'description':'OSINT', 'children': osint_data})

        return return_data


class SubdomainChangesSerializer(serializers.ModelSerializer):

    change = serializers.SerializerMethodField('get_change')

    is_interesting = serializers.SerializerMethodField('get_is_interesting')

    class Meta:
        model = Subdomain
        fields = '__all__'

    def get_change(self, Subdomain):
        return Subdomain.change

    def get_is_interesting(self, Subdomain):
        return get_interesting_subdomains(
            Subdomain.scan_history.id).filter(
            name=Subdomain.name).exists()


class EndPointChangesSerializer(serializers.ModelSerializer):

    change = serializers.SerializerMethodField('get_change')

    class Meta:
        model = EndPoint
        fields = '__all__'

    def get_change(self, EndPoint):
        return EndPoint.change


class InterestingSubdomainSerializer(serializers.ModelSerializer):

    class Meta:
        model = Subdomain
        fields = ['name']


class EmailSerializer(serializers.ModelSerializer):

    class Meta:
        model = Email
        fields = '__all__'


class DorkSerializer(serializers.ModelSerializer):

    class Meta:
        model = Dork
        fields = '__all__'


class EmployeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        fields = '__all__'


class MetafinderDocumentSerializer(serializers.ModelSerializer):

    class Meta:
        model = MetaFinderDocument
        fields = '__all__'
        depth = 1


class MetafinderUserSerializer(serializers.ModelSerializer):

    class Meta:
        model = MetaFinderDocument
        fields = ['author']


class InterestingEndPointSerializer(serializers.ModelSerializer):

    class Meta:
        model = EndPoint
        fields = ['http_url']


class TechnologyCountSerializer(serializers.Serializer):
    count = serializers.CharField()
    name = serializers.CharField()


class DorkCountSerializer(serializers.Serializer):
    count = serializers.CharField()
    type = serializers.CharField()


class TechnologySerializer(serializers.ModelSerializer):
    class Meta:
        model = Technology
        fields = '__all__'


class PortSerializer(serializers.ModelSerializer):
    class Meta:
        model = Port
        fields = '__all__'


class IpSerializer(serializers.ModelSerializer):

    ports = PortSerializer(many=True)

    class Meta:
        model = IpAddress
        fields = '__all__'


class IpSubdomainSerializer(serializers.ModelSerializer):

    class Meta:
        model = Subdomain
        fields = ['name', 'ip_addresses']
        depth = 1


class SubdomainSerializer(serializers.ModelSerializer):

    is_interesting = serializers.SerializerMethodField('get_is_interesting')

    endpoint_count = serializers.SerializerMethodField('get_endpoint_count')
    info_count = serializers.SerializerMethodField('get_info_count')
    low_count = serializers.SerializerMethodField('get_low_count')
    medium_count = serializers.SerializerMethodField('get_medium_count')
    high_count = serializers.SerializerMethodField('get_high_count')
    critical_count = serializers.SerializerMethodField('get_critical_count')
    ip_addresses = IpSerializer(many=True)
    technologies = TechnologySerializer(many=True)

    class Meta:
        model = Subdomain
        fields = '__all__'

    def get_is_interesting(self, Subdomain):
        return get_interesting_subdomains(
            Subdomain.scan_history.id).filter(
            name=Subdomain.name).exists()

    def get_endpoint_count(self, Subdomain):
        return Subdomain.get_endpoint_count

    def get_info_count(self, Subdomain):
        return Subdomain.get_info_count

    def get_low_count(self, Subdomain):
        return Subdomain.get_low_count

    def get_medium_count(self, Subdomain):
        return Subdomain.get_medium_count

    def get_high_count(self, Subdomain):
        return Subdomain.get_high_count

    def get_critical_count(self, Subdomain):
        return Subdomain.get_critical_count


class EndpointSerializer(serializers.ModelSerializer):

    class Meta:
        model = EndPoint
        fields = '__all__'


class VulnerabilitySerializer(serializers.ModelSerializer):

    discovered_date = serializers.SerializerMethodField()

    severity = serializers.SerializerMethodField()

    def get_discovered_date(self, Vulnerability):
        return Vulnerability.discovered_date.strftime("%b %d, %Y %H:%M")

    def get_severity(self, Vulnerability):
        if Vulnerability.severity == 0:
            return "Info"
        elif Vulnerability.severity == 1:
            return "Low"
        elif Vulnerability.severity == 2:
            return "Medium"
        elif Vulnerability.severity == 3:
            return "High"
        elif Vulnerability.severity == 4:
            return "Critical"

    class Meta:
        model = Vulnerability
        fields = '__all__'

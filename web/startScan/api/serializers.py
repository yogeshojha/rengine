from rest_framework import serializers
from startScan.models import *
from reNgine.common_func import *


class VisualisePortSerializer(serializers.ModelSerializer):

    name = serializers.SerializerMethodField('get_name')

    class Meta:
        model = Port
        fields = [
            'name'
        ]

    def get_name(self, port):
        return str(port.number) + "/" + port.service_name


class VisualiseIpSerializer(serializers.ModelSerializer):

    name = serializers.SerializerMethodField('get_name')
    children = serializers.SerializerMethodField('get_children')

    class Meta:
        model = IpAddress
        fields = [
            'name',
            'children'
        ]

    def get_name(self, Ip):
        return Ip.address

    def get_children(self, ip):
        port = Port.objects.filter(ports__in=IpAddress.objects.filter(address=ip))
        serializer = VisualisePortSerializer(port, many=True)
        return serializer.data


class VisualiseEndpointSerializer(serializers.ModelSerializer):

    name = serializers.SerializerMethodField('get_name')

    class Meta:
        model = EndPoint
        fields = [
            'name'
        ]

    def get_name(self, endpoint):
        return endpoint.http_url


class VisualiseSubdomainSerializer(serializers.ModelSerializer):

    children = serializers.SerializerMethodField('get_children')

    class Meta:
        model = Subdomain
        fields = [
            'name',
            'children'
        ]

    def get_children(self, subdomain_name):
        subdomain = Subdomain.objects.filter(
            scan_history=self.context.get('scan_history')).filter(name=subdomain_name)
        ips = IpAddress.objects.filter(ip_addresses__in=subdomain)
        ip_serializer = VisualiseIpSerializer(ips, many=True)

        endpoint = EndPoint.objects.filter(
            scan_history=self.context.get('scan_history')).filter(subdomain__name=subdomain_name)
        endpoint_serializer = VisualiseEndpointSerializer(endpoint, many=True)

        return [
                {'name': 'IPs', 'children': ip_serializer.data},
                {'name': 'Endpoints', 'children': endpoint_serializer.data},
                {'name': 'Screenshot', 'children': []}
            ]

class VisualiseDataSerializer(serializers.ModelSerializer):

    name = serializers.SerializerMethodField('get_name')
    children = serializers.SerializerMethodField('get_children')

    class Meta:
        model = ScanHistory
        fields = [
            'name',
            'children',
        ]

    def get_name(self, ScanHistory):
        return ScanHistory.domain.name

    def get_children(self, ScanHistory):
        subdomain = Subdomain.objects.filter(scan_history=ScanHistory)
        serializer = VisualiseSubdomainSerializer(subdomain, many=True, context={'scan_history': ScanHistory})
        return [
                {'name': 'Subdomains', 'children': serializer.data},
                {'name': 'OSINT', 'children': []}
            ]



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

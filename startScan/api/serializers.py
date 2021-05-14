from rest_framework import serializers

from startScan.models import Subdomain, ScanHistory, EndPoint, Vulnerability

from reNgine.common_func import *


class SubdomainSerializer(serializers.ModelSerializer):

    is_interesting = serializers.SerializerMethodField('get_is_interesting')

    endpoint_count = serializers.SerializerMethodField('get_endpoint_count')
    info_count = serializers.SerializerMethodField('get_info_count')
    low_count = serializers.SerializerMethodField('get_low_count')
    medium_count = serializers.SerializerMethodField('get_medium_count')
    high_count = serializers.SerializerMethodField('get_high_count')
    critical_count = serializers.SerializerMethodField('get_critical_count')
    total_vulnerability_count = serializers.SerializerMethodField(
        'get_total_vulnerability_count')

    class Meta:
        model = Subdomain
        fields = '__all__'
        # lookup_field = 'scan_history'

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

    def get_total_vulnerability_count(self, Subdomain):
        return 50


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

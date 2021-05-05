from rest_framework import serializers

from startScan.models import Subdomain, ScanHistory, EndPoint, Vulnerability

from reNgine.common_func import *

class ScanHistorySerializer(serializers.ModelSerializer):

    is_interesting = serializers.SerializerMethodField('get_is_interesting')

    class Meta:
        model = Subdomain
        fields = '__all__'
        # lookup_field = 'scan_history'

    def get_is_interesting(self, Subdomain):
        return get_interesting_subdomains(Subdomain.scan_history.id).filter(name=Subdomain.name).exists()


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

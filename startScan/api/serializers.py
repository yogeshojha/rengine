from rest_framework import serializers

from startScan.models import ScannedHost, ScanHistory, WayBackEndPoint, VulnerabilityScan

from reNgine.common_func import *

class ScanHistorySerializer(serializers.ModelSerializer):

    is_interesting = serializers.SerializerMethodField('get_is_interesting')

    class Meta:
        model = ScannedHost
        fields = '__all__'
        # lookup_field = 'scan_history'

    def get_is_interesting(self, ScannedHost):
        return get_interesting_subdomains(ScannedHost.scan_history.id).filter(subdomain=ScannedHost.subdomain).exists()


class EndpointSerializer(serializers.ModelSerializer):

    class Meta:
        model = WayBackEndPoint
        fields = '__all__'


class VulnerabilitySerializer(serializers.ModelSerializer):

    discovered_date = serializers.SerializerMethodField()

    severity = serializers.SerializerMethodField()

    def get_discovered_date(self, VulnerabilityScan):
        return VulnerabilityScan.discovered_date.strftime("%b %d, %Y %H:%M")

    def get_severity(self, VulnerabilityScan):
        if VulnerabilityScan.severity == 0:
            return "Info"
        elif VulnerabilityScan.severity == 1:
            return "Low"
        elif VulnerabilityScan.severity == 2:
            return "Medium"
        elif VulnerabilityScan.severity == 3:
            return "High"
        elif VulnerabilityScan.severity == 4:
            return "Critical"

    class Meta:
        model = VulnerabilityScan
        fields = '__all__'

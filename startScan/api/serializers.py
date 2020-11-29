from rest_framework import serializers

from startScan.models import ScannedHost, ScanHistory, WayBackEndPoint, VulnerabilityScan


class ScanHistorySerializer(serializers.ModelSerializer):

    class Meta:
        model = ScannedHost
        fields = '__all__'
        # lookup_field = 'scan_history'


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

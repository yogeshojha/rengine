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

    def get_discovered_date(self, VulnerabilityScan):
        return VulnerabilityScan.discovered_date.strftime("%b %d, %Y %H:%M")

    class Meta:
        model = VulnerabilityScan
        fields = '__all__'

from rest_framework import serializers

from startScan.models import ScannedHost, ScanHistory


class ScanHistorySerializer(serializers.ModelSerializer):
    
    class Meta:
        model = ScannedHost
        fields = '__all__'
        # lookup_field = 'scan_history'

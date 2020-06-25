from rest_framework import serializers

from startScan.models import ScannedHost, ScanHistory


class ScannedHostSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScannedHost
        fields = '__all__'

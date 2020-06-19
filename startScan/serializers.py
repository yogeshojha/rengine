from rest_framework import serializers

from .models import ScannedHost, ScanHistory

class ScannedHostSerializer(serializers.ModelSerializer):

    # scan_history = serializers.SerializerMethodField()
    #
    # def get_scan_history(self, scanned_host):
    #     return scanned_host.scan_history.domain_name.domain_name

    id = serializers.IntegerField(read_only=True)

    class Meta:
        model = ScannedHost
        fields = '__all__'

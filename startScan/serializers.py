from rest_framework import serializers

from .models import ScannedHost, ScanHistory

class ScannedHostSerializer(serializers.ModelSerializer):

    id = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = ScannedHost
        fields = '__all__'

from startScan.api.serializers import ScanHistorySerializer
from rest_framework import viewsets
from startScan.models import ScannedHost, ScanHistory
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view, action

class ScanHistoryViewSet(viewsets.ModelViewSet):
    queryset = ScannedHost.objects.all()
    serializer_class = ScanHistorySerializer

    def get_queryset(self):
        req = self.request
        scan_id = req.query_params.get('scan_id')
        if scan_id:
            self.queryset = ScannedHost.objects.filter(scan_history__id=scan_id)
            return self.queryset
        else:
            return self.queryset

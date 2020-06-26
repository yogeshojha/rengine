from startScan.api.serializers import ScanHistorySerializer
from rest_framework import viewsets
from startScan.models import ScannedHost, ScanHistory
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view, action

@api_view(['GET', ])
def api_scan_host_detailed_view(request, id):
    try:
        scanned_host = ScannedHost.objects.filter(scan_history__id=id)
    except:
        return Response(status=status.HTTP_404_NOT_FOUND)

    serializer = ScanHistorySerializer(scanned_host, many=True)
    return Response(serializer.data)


class ScanHistoryViewSet(viewsets.ModelViewSet):
    queryset = ScannedHost.objects.all()
    serializer_class = ScanHistorySerializer

    @action(detail=True)
    def scan_list(self, request, pk=None):
        scan_history = ScannedHost.objects.filter(scan_history__id=pk)
        scan_json = ScanHistorySerializer(scan_history, many=True)
        return Response(scan_json.data)
    # lookup_field = 'scan_history'

from startScan.api.serializers import ScannedHostSerializer
from rest_framework import viewsets
from startScan.models import ScannedHost
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view

@api_view(['GET', ])
def api_scan_host_detailed_view(request, id):
    try:
        scanned_host = ScannedHost.objects.filter(scan_history__id=id)
    except:
        return Response(status=status.HTTP_404_NOT_FOUND)

    serializer = ScannedHostSerializer(scanned_host, many=True)
    return Response(serializer.data)

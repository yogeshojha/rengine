from django.shortcuts import render
from django.http import HttpResponse
from startScan.models import ScanHistory, WayBackEndPoint, ScannedHost
from targetApp.models import Domain


def index(request):
    domain_count = Domain.objects.all().count()
    endpoint_count = WayBackEndPoint.objects.all().count()
    scan_count = ScanHistory.objects.all().count()
    subdomain_count = ScannedHost.objects.all().count()
    alive_count = ScannedHost.objects.all().exclude(http_status__exact=0).count()
    context = {"dashboard_data_active": "true",
            'domain_count': domain_count,
            'endpoint_count': endpoint_count,
            'scan_count': scan_count,
            'subdomain_count': subdomain_count,
            'alive_count': alive_count
        }
    return render(request, 'dashboard/index.html', context)

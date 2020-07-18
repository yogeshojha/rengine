from django.shortcuts import render
from django.http import HttpResponse
from startScan.models import ScanHistory, WayBackEndPoint, ScannedHost
from targetApp.models import Domain


def index(request):
    domain_count = Domain.objects.all().count()
    endpoint_count = WayBackEndPoint.objects.all().count()
    scan_count = ScanHistory.objects.all().count()
    subdomain_count = ScannedHost.objects.all().count()
    alive_count = \
        ScannedHost.objects.all().exclude(http_status__exact=0).count()
    endpoint_alive_count = \
        WayBackEndPoint.objects.filter(http_status__exact=200).count()
    on_going_scan_count = \
        ScanHistory.objects.filter(scan_status=1).count()
    recent_scans = ScanHistory.objects.all().order_by('-last_scan_date')[:4]
    context = {
        'dashboard_data_active': 'true',
        'domain_count': domain_count,
        'endpoint_count': endpoint_count,
        'scan_count': scan_count,
        'subdomain_count': subdomain_count,
        'alive_count': alive_count,
        'endpoint_alive_count': endpoint_alive_count,
        'on_going_scan_count': on_going_scan_count,
        'recent_scans': recent_scans, }
    return render(request, 'dashboard/index.html', context)

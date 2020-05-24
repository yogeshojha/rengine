from django.shortcuts import render, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse, HttpResponseRedirect
from django.urls import reverse
from .models import ScanHistory, ScannedSubdomains
from notification.models import NotificationHooks
from targetApp.models import Domain
from scanEngine.models import EngineType
import threading
from . import sublist3r
from django.utils import timezone
import requests
import json

def index(request):
    return render(request, 'startScan/index.html')

def scan_history(request):
    scan_history = ScanHistory.objects
    context = {'scan_history_active': 'true', "scan_history":scan_history}
    return render(request, 'startScan/history.html', context)

def detail_scan(request, id):
    subdomain_details = ScannedSubdomains.objects.filter(scan_history__id=id)
    context = {'scan_history_active': 'true', 'subdomain':subdomain_details}
    return render(request, 'startScan/detail_scan.html', context)

def start_scan_ui(request, id):
    domain = get_object_or_404(Domain, id=id)
    if request.method == "POST":
        # get engine type
        engine_type = request.POST['scan_mode']
        engine_object = get_object_or_404(EngineType, id=engine_type)
        task = ScanHistory()
        task.scan_status = 1
        task.domain_name = domain
        task.scan_type = engine_object
        task.last_scan_date = timezone.now()
        task.save()
        # save last scan for domain model
        domain.last_scan_date = timezone.now()
        domain.save()
        t = threading.Thread(target=doScan, args=[task.id, domain])
        t.setDaemon(True)
        t.start()
        messages.add_message(request, messages.INFO, 'Scan Started for ' + domain.domain_name)
        return HttpResponseRedirect(reverse('scan_history'))
    engine = EngineType.objects
    context = {'scan_history_active': 'true', 'domain': domain, 'engines': engine}
    return render(request, 'startScan/start_scan_ui.html', context)

def doScan(id, domain):
    task = ScanHistory.objects.get(pk=id)
    notif_hook = NotificationHooks.objects.filter(send_notif=True)
    subdomains = sublist3r.main(domain.domain_name, 40, 'hello.txt', ports= None, silent=False, verbose= False, enable_bruteforce= False, engines=None)
    for subdomain in subdomains:
        scanned = ScannedSubdomains()
        scanned.subdomain = subdomain
        scanned.scan_history = task
        scanned.open_ports = "80"
        scanned.takeover_possible = False
        scanned.http_status = 200
        scanned.alive_subdomain = True
        scanned.technology_stack = "Test"
        scanned.save()
    task.scan_status = 2
    task.save()

    # notify on slack
    scan_status_msg = {'text': "reEngine finished scanning " + domain.domain_name}
    headers = {'content-type': 'application/json'}
    for notif in notif_hook:
        requests.post(notif.hook_url, data=json.dumps(scan_status_msg), headers=headers)

def checkScanStatus(request, id):
    task = Crawl.objects.get(pk=id)
    return JsonResponse({'is_done':task.is_done, result:task.result})

from django.shortcuts import render, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse, HttpResponseRedirect
from django.urls import reverse
from .models import ScanHistory, ScannedHost, ScannedSubdomainWithProtocols
from notification.models import NotificationHooks
from targetApp.models import Domain
from scanEngine.models import EngineType
import threading
from django.utils import timezone
from datetime import datetime
import requests
import json
import os

def index(request):
    return render(request, 'startScan/index.html')

def scan_history(request):
    scan_history = ScanHistory.objects
    context = {'scan_history_active': 'true', "scan_history":scan_history}
    return render(request, 'startScan/history.html', context)

def detail_scan(request, id):
    subdomain_details = ScannedHost.objects.filter(scan_history__id=id)
    subdomain_aqua_details = ScannedSubdomainWithProtocols.objects.filter(host__scan_history__id=id)
    context = {'scan_history_active': 'true', 'subdomain':subdomain_details, 'alive': subdomain_aqua_details}
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
    results_dir = '/app/tools/scan_results/'
    os.chdir(results_dir)
    try:
        current_scan_dir = domain.domain_name+'__'+str(datetime.strftime(timezone.now(), '%Y_%m_%d_%H_%M_%S'))
        os.mkdir(current_scan_dir)
    except:
        # do something here
        print("Oops!")
    # all scan happens here
    os.system('/app/tools/get_subdomain.sh %s %s' %(domain.domain_name, current_scan_dir))

    scan_results_file = results_dir+current_scan_dir+'/sorted_subdomain_collection.txt'
    with open(scan_results_file) as subdomain_list:
        for subdomain in subdomain_list:
            scanned = ScannedHost()
            scanned.subdomain = subdomain.rstrip('\n')
            scanned.scan_history = task
            scanned.takeover_possible = False
            scanned.save()
    # after subdomain discovery run aquatone for visual identification
    with_protocol_path = results_dir + current_scan_dir + '/with_protocol_domains.txt'
    output_aquatone_path = results_dir + current_scan_dir + '/aquascreenshots/'
    aquatone_command = 'cat {} | /app/tools/aquatone -ports xlarge -out {}'.format(with_protocol_path, output_aquatone_path)
    os.system(aquatone_command)

    aqua_json_path = output_aquatone_path + '/aquatone_session.json'
    with open(aqua_json_path, 'r') as json_file:
        data = json.load(json_file)
    subdomain_details = ScannedHost.objects.filter(scan_history__id=id)

    # should be a better way for this
    for sub in subdomain_details:
        for host in data['pages']:
            if sub.subdomain == data['pages'][host]['hostname']:
                subdomain_proto = ScannedSubdomainWithProtocols()
                subdomain_proto.host = sub
                subdomain_proto.url = data['pages'][host]['url']
                subdomain_proto.ip_address = data['pages'][host]['addrs']
                subdomain_proto.page_title = data['pages'][host]['pageTitle']
                subdomain_proto.http_status = data['pages'][host]['status'][0:3]
                subdomain_proto.screenshot_path = data['pages'][host]['screenshotPath']
                subdomain_proto.technology_stack = 'fake'
                subdomain_proto.save()

    task.scan_status = 2
    task.save()
    # notify on slack
    # scan_status_msg = {'text': "reEngine finished scanning " + domain.domain_name}
    # headers = {'content-type': 'application/json'}
    # for notif in notif_hook:
    #     requests.post(notif.hook_url, data=json.dumps(scan_status_msg), headers=headers)

def checkScanStatus(request, id):
    task = Crawl.objects.get(pk=id)
    return JsonResponse({'is_done':task.is_done, result:task.result})

from django.shortcuts import render, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse, HttpResponseRedirect
from django.urls import reverse
from .models import ScanHistory, ScannedHost, ScanActivity, WayBackEndPoint
from notification.models import NotificationHooks
from targetApp.models import Domain
from scanEngine.models import EngineType
import threading
from django.utils import timezone, dateformat
from datetime import datetime
import requests
import json
import os
from rest_framework import viewsets
from .serializers import ScannedHostSerializer

def index(request):
    return render(request, 'startScan/index.html')

def scan_history(request):
    scan_history = ScanHistory.objects
    context = {'scan_history_active': 'true', "scan_history":scan_history}
    return render(request, 'startScan/history.html', context)

def detail_scan(request, id):
    subdomain_details = ScannedHost.objects.filter(scan_history__id=id)
    # alive_count = ScannedHost.objects.filter(scan_history__id=id).exclude(http_status__exact=0).count()
    # scan_activity = ScanActivity.objects.filter(scan_of__id=id)
    # endpoints = WayBackEndPoint.objects.filter(url_of__id=id)
    # context = {'scan_history_active': 'true',
    #             'subdomain':subdomain_details,
    #             'scan_history':scan_history,
    #             'scan_activity':scan_activity,
    #             'alive_count':alive_count,
    #             'endpoints':endpoints
    #             }
    context = {
                'scan_history_active': 'true',
    }
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
    save_scan_activity(task, "Scanning Started", 2)

    notif_hook = NotificationHooks.objects.filter(send_notif=True)
    results_dir = '/app/tools/scan_results/'
    os.chdir(results_dir)
    try:
        current_scan_dir = domain.domain_name+'_'+str(datetime.strftime(timezone.now(), '%Y_%m_%d_%H_%M_%S'))
        os.mkdir(current_scan_dir)
    except:
        # do something here
        print("Oops!")

    save_scan_activity(task, "Subdomain Scanning", 1)
    # all subdomain scan happens here
    os.system('/app/tools/get_subdomain.sh %s %s' %(domain.domain_name, current_scan_dir))

    subdomain_scan_results_file = results_dir + current_scan_dir + '/sorted_subdomain_collection.txt'

    with open(subdomain_scan_results_file) as subdomain_list:
        for subdomain in subdomain_list:
            scanned = ScannedHost()
            scanned.subdomain = subdomain.rstrip('\n')
            scanned.scan_history = task
            scanned.save()

    update_last_activity()
    save_scan_activity(task, "Port Scanning", 1)

    # after all subdomain has been discovered run naabu to discover the ports
    port_results_file = results_dir + current_scan_dir + '/ports.json'

    naabu_command = 'cat {} | /app/tools/naabu -oJ -o {}'.format(subdomain_scan_results_file, port_results_file)
    os.system(naabu_command)

    # writing port results
    try:
        port_json_result = open(port_results_file, 'r')
        lines = port_json_result.readlines()
        for line in lines:
            try:
                json_st = json.loads(line.strip())
            except:
                json_st = "{'host':'','port':''}"
            sub_domain = ScannedHost.objects.get(scan_history=task, subdomain=json_st['host'])
            if sub_domain.open_ports:
                sub_domain.open_ports = sub_domain.open_ports + ',' + str(json_st['port'])
            else:
                sub_domain.open_ports = str(json_st['port'])
            sub_domain.save()
    except:
        print('Port File doesnt exist')

    update_last_activity()
    save_scan_activity(task, "HTTP Crawler", 1)

    # once port scan is complete then run httpx, this has to run in background thread later
    httpx_results_file = results_dir + current_scan_dir + '/httpx.json'

    httpx_command = 'cat {} | /app/tools/httpx -json -o {}'.format(subdomain_scan_results_file, httpx_results_file)
    os.system(httpx_command)


    # alive subdomains from httpx
    alive_file_location = results_dir + current_scan_dir + '/alive.txt'
    alive_file = open(alive_file_location, 'w')

    # writing httpx results
    httpx_json_result = open(httpx_results_file, 'r')
    lines = httpx_json_result.readlines()
    for line in lines:
        json_st = json.loads(line.strip())
        sub_domain = ScannedHost.objects.get(scan_history=task, subdomain=json_st['url'].split("//")[-1])
        sub_domain.http_url = json_st['url']
        sub_domain.http_status = json_st['status-code']
        sub_domain.page_title = json_st['title']
        sub_domain.content_length = json_st['content-length']
        alive_file.write(json_st['url']+'\n')
        sub_domain.save()
    alive_file.close()

    update_last_activity()
    save_scan_activity(task, "Visual Recon - Screenshot", 1)

    # after subdomain discovery run aquatone for visual identification
    with_protocol_path = results_dir + current_scan_dir + '/alive.txt'
    output_aquatone_path = results_dir + current_scan_dir + '/aquascreenshots/'
    aquatone_command = 'cat {} | /app/tools/aquatone --threads 5 -ports xlarge -out {}'.format(with_protocol_path, output_aquatone_path)
    os.system(aquatone_command)

    aqua_json_path = output_aquatone_path + '/aquatone_session.json'
    with open(aqua_json_path, 'r') as json_file:
        data = json.load(json_file)

    for host in data['pages']:
        sub_domain = ScannedHost.objects.get(scan_history__id=id, subdomain=data['pages'][host]['hostname'])
        list_ip = data['pages'][host]['addrs']
        ip_string = ','.join(list_ip)
        sub_domain.ip_address = ip_string
        sub_domain.screenshot_path = current_scan_dir + '/aquascreenshots/' + data['pages'][host]['screenshotPath']
        sub_domain.http_header_path = current_scan_dir + '/aquascreenshots/' + data['pages'][host]['headersPath']
        tech_list = []
        if data['pages'][host]['tags'] is not None:
            for tag in data['pages'][host]['tags']:
                tech_list.append(tag['text'])
        tech_string = ','.join(tech_list)
        sub_domain.technology_stack = tech_string
        sub_domain.save()


    # get endpoints from wayback engine
    update_last_activity()
    save_scan_activity(task, "Fetching endpoints", 1)
    wayback_results_file = results_dir + current_scan_dir + '/wayback.json'

    wayback_command = 'echo ' + domain.domain_name + ' | /app/tools/gau -providers wayback | /app/tools/httpx -status-code -content-length -title -json -o {}'.format(wayback_results_file)
    os.system(wayback_command)

    wayback_json_result = open(wayback_results_file, 'r')
    lines = wayback_json_result.readlines()
    for line in lines:
        json_st = json.loads(line.strip())
        endpoint = WayBackEndPoint()
        endpoint.url_of = task
        endpoint.http_url = json_st['url']
        endpoint.content_length = json_st['content-length']
        endpoint.http_status = json_st['status-code']
        endpoint.page_title = json_st['title']
        endpoint.save()



    task.scan_status = 2
    task.save()

    # notify on slack
    scan_status_msg = {'text': "reEngine finished scanning " + domain.domain_name}
    headers = {'content-type': 'application/json'}
    for notif in notif_hook:
        requests.post(notif.hook_url, data=json.dumps(scan_status_msg), headers=headers)
    update_last_activity()
    save_scan_activity(task, "Scan Completed", 2)

def checkScanStatus(request, id):
    task = Crawl.objects.get(pk=id)
    return JsonResponse({'is_done':task.is_done, result:task.result})

def save_scan_activity(task, message, status):
    scan_activity = ScanActivity()
    scan_activity.scan_of = task
    scan_activity.title = message
    scan_activity.time = dateformat.format(timezone.now(), 'M d H:i')
    scan_activity.status = status
    scan_activity.save()

def update_last_activity():
    #save the last activity as successful
    last_activity = ScanActivity.objects.latest('id')
    last_activity.status = 2
    last_activity.save()


class ScannedHostViewSet(viewsets.ModelViewSet):
    serializer_class = ScannedHostSerializer
    queryset = ScannedHost.objects.all()

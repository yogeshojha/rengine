from django.shortcuts import render, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse, HttpResponseRedirect, HttpResponse
from django.urls import reverse
from .models import ScanHistory, ScannedHost, ScanActivity, WayBackEndPoint
from notification.models import NotificationHooks
from targetApp.models import Domain
from scanEngine.models import EngineType
import threading
from django.utils import timezone, dateformat
from datetime import datetime
import os, traceback, json, requests
def index(request):
    return render(request, 'startScan/index.html')

def scan_history(request):
    host = ScanHistory.objects
    context = {'scan_history_active': 'true', "scan_history": host}
    return render(request, 'startScan/history.html', context)

def detail_scan(request, id):
    subdomain_count = ScannedHost.objects.filter(scan_history__id=id).count()
    alive_count = ScannedHost.objects.filter(scan_history__id=id).exclude(http_status__exact=0).count()
    scan_activity = ScanActivity.objects.filter(scan_of__id=id).order_by('time')
    endpoint_count = WayBackEndPoint.objects.filter(url_of__id=id).count()
    endpoint_alive_count = WayBackEndPoint.objects.filter(url_of__id=id, http_status__exact=200).count()
    history = get_object_or_404(ScanHistory, id=id)
    context = {'scan_history_active': 'true',
                'scan_history': scan_history,
                'scan_activity': scan_activity,
                'alive_count': alive_count,
                'scan_history_id': id,
                'subdomain_count': subdomain_count,
                'endpoint_count': endpoint_count,
                'endpoint_alive_count':  endpoint_alive_count,
                'history': history,
                }
    return render(request, 'startScan/detail_scan.html', context)

def start_scan_ui(request, host_id):
    domain = get_object_or_404(Domain, id=host_id)
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
    custom_engine_count = EngineType.objects.filter(default_engine=False).count()
    context = {'scan_history_active': 'true', 'domain': domain, 'engines': engine, 'custom_engine_count': custom_engine_count}
    return render(request, 'startScan/start_scan_ui.html', context)

def doScan(host_id, domain):
    task = ScanHistory.objects.get(pk=host_id)

    create_scan_activity(task, "Scanning Started", 2)

    notif_hook = NotificationHooks.objects.filter(send_notif=True)
    results_dir = '/app/tools/scan_results/'
    os.chdir(results_dir)
    try:
        current_scan_dir = domain.domain_name+'_'+str(datetime.strftime(timezone.now(), '%Y_%m_%d_%H_%M_%S'))
        os.mkdir(current_scan_dir)
    except:
        # do something here
        scan_failed(task)

    try:
        # TODO make subdomain only scan
        '''
        currently subdomain scan is by default, in next release this may be removed
        So that recon can be done on single subdomain
        rather than the entire subdomain
        '''
        if(task.scan_type.subdomain_discovery):
            create_scan_activity(task, "Subdomain Scanning", 1)
            # all subdomain scan happens here
            os.system('/app/tools/get_subdomain.sh %s %s' %(domain.domain_name, current_scan_dir))

            subdomain_scan_results_file = results_dir + current_scan_dir + '/sorted_subdomain_collection.txt'

            with open(subdomain_scan_results_file) as subdomain_list:
                for subdomain in subdomain_list:
                    scanned = ScannedHost()
                    scanned.subdomain = subdomain.rstrip('\n')
                    scanned.scan_history = task
                    scanned.save()

        if(task.scan_type.port_scan):
            update_last_activity()
            create_scan_activity(task, "Port Scanning", 1)

            # after all subdomain has been discovered run naabu to discover the ports
            port_results_file = results_dir + current_scan_dir + '/ports.json'

            naabu_command = 'cat {} | naabu -json -o {}'.format(subdomain_scan_results_file, port_results_file)
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
                print('No Ports file')

        '''
        HTTP Crawlwer and screenshot will run by default
        '''
        update_last_activity()
        create_scan_activity(task, "HTTP Crawler", 1)

        # once port scan is complete then run httpx, TODO this has to run in background thread later
        httpx_results_file = results_dir + current_scan_dir + '/httpx.json'

        httpx_command = 'cat {} | httpx -json -o {}'.format(subdomain_scan_results_file, httpx_results_file)
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
        create_scan_activity(task, "Visual Recon - Screenshot", 1)

        # after subdomain discovery run aquatone for visual identification
        with_protocol_path = results_dir + current_scan_dir + '/alive.txt'
        output_aquatone_path = results_dir + current_scan_dir + '/aquascreenshots/'
        aquatone_command = 'cat {} | /app/tools/aquatone --threads 5 -ports xlarge -out {}'.format(with_protocol_path, output_aquatone_path)
        os.system(aquatone_command)

        aqua_json_path = output_aquatone_path + '/aquatone_session.json'
        with open(aqua_json_path, 'r') as json_file:
            data = json.load(json_file)

        for host in data['pages']:
            sub_domain = ScannedHost.objects.get(scan_history__id=host_id, subdomain=data['pages'][host]['hostname'])
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

        '''
        Directory search is not provided by default, check for conditions
        '''
        if(task.scan_type.dir_file_search):
            update_last_activity()
            create_scan_activity(task, "Directory Search", 1)
            # scan directories for all the alive subdomain with http status > 200
            alive_subdomains = ScannedHost.objects.filter(scan_history__id=host_id).exclude(http_url='')
            dirs_results = current_scan_dir + '/dirs.json'
            for subdomain in alive_subdomains:
                os.system('/app/tools/get_dirs.sh %s %s' %(subdomain.http_url, dirs_results))
                try:
                    with open(dirs_results, "r") as json_file:
                        json_string = json_file.read()
                        scanned_host = ScannedHost.objects.get(scan_history__id=host_id, http_url=subdomain.http_url)
                        scanned_host.directory_json = json_string
                        scanned_host.save()
                except:
                    print("No File")


        '''
        Getting endpoint from GAU, is also not set by default, check for conditions.
        One thing to change is that, currently in gau, providers is set to wayback,
        later give them choice
        '''
        # TODO: give providers as choice for users between commoncrawl, alienvault or wayback
        if(task.scan_type.fetch_url):
            update_last_activity()
            create_scan_activity(task, "Fetching endpoints", 1)
            wayback_results_file = results_dir + current_scan_dir + '/url_wayback.json'

            '''
            It first runs gau to gather all urls from wayback, then we will use hakrawler to identify more urls
            '''
            os.system('/app/tools/get_urls.sh %s %s' %(domain.domain_name, current_scan_dir))

            url_results_file = results_dir + current_scan_dir + '/all_urls.json'

            urls_json_result = open(url_results_file, 'r')
            lines = urls_json_result.readlines()
            for line in lines:
                json_st = json.loads(line.strip())
                endpoint = WayBackEndPoint()
                endpoint.url_of = task
                endpoint.http_url = json_st['url']
                endpoint.content_length = json_st['content-length']
                endpoint.http_status = json_st['status-code']
                endpoint.page_title = json_st['title']
                endpoint.save()

        '''
        Once the scan is completed, save the status to successful
        '''
        task.scan_status = 2
        task.save()
    except Exception as e:
        print(traceback.format_exc())
        scan_failed(task)

    # notify on slack
    scan_status_msg = {'text': "reEngine finished scanning " + domain.domain_name}
    headers = {'content-type': 'application/json'}
    for notif in notif_hook:
        requests.post(notif.hook_url, data=json.dumps(scan_status_msg), headers=headers)
    update_last_activity()
    create_scan_activity(task, "Scan Completed", 2)

def checkScanStatus(request, id):
    task = Crawl.objects.get(pk=id)
    return JsonResponse({'is_done':task.is_done, result:task.result})

def scan_failed(task):
    task.scan_status = 0
    task.save()

def create_scan_activity(task, message, status):
    scan_activity = ScanActivity()
    scan_activity.scan_of = task
    scan_activity.title = message
    scan_activity.time = timezone.now()
    scan_activity.status = status
    scan_activity.save()

def update_last_activity():
    #save the last activity as successful
    last_activity = ScanActivity.objects.latest('id')
    last_activity.status = 2
    last_activity.time = timezone.now()
    last_activity.save()

def export_subdomains(request, scan_id):
    subdomain_list = ScannedHost.objects.filter(scan_history__id=scan_id)
    domain_results = ScanHistory.objects.get(id=scan_id)
    response_body = ""
    for subdomain in subdomain_list:
        response_body = response_body + subdomain.subdomain + "\n"
    response = HttpResponse(response_body, content_type='text/plain')
    response['Content-Disposition'] = 'attachment; filename="subdomains_'+domain_results.domain_name.domain_name+'_'+str(domain_results.last_scan_date.date())+'.txt"'
    return response

def export_endpoints(request, scan_id):
    endpoint_list = WayBackEndPoint.objects.filter(url_of__id=scan_id)
    domain_results = ScanHistory.objects.get(id=scan_id)
    response_body = ""
    for endpoint in endpoint_list:
        response_body = response_body + endpoint.http_url + "\n"
    response = HttpResponse(response_body, content_type='text/plain')
    response['Content-Disposition'] = 'attachment; filename="endpoints_'+domain_results.domain_name.domain_name+'_'+str(domain_results.last_scan_date.date())+'.txt"'
    return response

def export_urls(request, scan_id):
    urls_list = ScannedHost.objects.filter(scan_history__id=scan_id)
    domain_results = ScanHistory.objects.get(id=scan_id)
    response_body = ""
    for url in urls_list:
        if url.http_url:
            response_body = response_body + url.http_url + "\n"
    response = HttpResponse(response_body, content_type='text/plain')
    response['Content-Disposition'] = 'attachment; filename="urls_'+domain_results.domain_name.domain_name+'_'+str(domain_results.last_scan_date.date())+'.txt"'
    return response

def delete_scan(request, id):
    obj = get_object_or_404(ScanHistory, id=id)
    if request.method == "POST":
        obj.delete()
        messageData = {'status': 'true'}
        messages.add_message(request, messages.INFO, 'Scan history successfully deleted!')
    else:
        messageData = {'status': 'false'}
        messages.add_message(request, messages.INFO, 'Oops! something went wrong!')
    return JsonResponse(messageData)

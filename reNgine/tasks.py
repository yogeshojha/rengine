import os
import traceback
import yaml
import json
from celery import shared_task
from reNgine.celery import app
from startScan.models import ScanHistory, ScannedHost, ScanActivity, WayBackEndPoint
from targetApp.models import Domain
from notification.models import NotificationHooks
from django.conf import settings
from django.utils import timezone, dateformat
from datetime import datetime

'''
task for background scan
'''


@app.task
def doScan(host_id, domain_id):
    print(doScan.request.id)
    task = ScanHistory.objects.get(pk=host_id)
    domain = Domain.objects.get(pk=domain_id)

    create_scan_activity(task, "Scanning Started", 2)

    notif_hook = NotificationHooks.objects.filter(send_notif=True)
    results_dir = settings.TOOL_LOCATION + 'scan_results/'
    os.chdir(results_dir)
    try:
        current_scan_dir = domain.domain_name + '_' + \
            str(datetime.strftime(timezone.now(), '%Y_%m_%d_%H_%M_%S'))
        os.mkdir(current_scan_dir)
    except BaseException:
        # do something here
        scan_failed(task)

    try:
        yaml_configuration = yaml.load(
            task.scan_type.yaml_configuration,
            Loader=yaml.FullLoader)
        if(task.scan_type.subdomain_discovery):
            create_scan_activity(task, "Subdomain Scanning", 1)

            # check for all the tools and add them into string
            # if tool selected is all then make string, no need for loop
            if 'all' in yaml_configuration['subdomain_discovery']['uses_tool']:
                tools = 'amass-active amass-passive assetfinder sublist3r subfinder'
            else:
                tools = ' '.join(
                    str(tool) for tool in yaml_configuration['subdomain_discovery']['uses_tool'])

            # check for thread, by default should be 10
            if yaml_configuration['subdomain_discovery']['thread'] > 0:
                threads = yaml_configuration['subdomain_discovery']['thread']
            else:
                threads = 10

            if 'amass-active' in tools:
                if ('wordlist' not in yaml_configuration['subdomain_discovery']
                    or not yaml_configuration['subdomain_discovery']['wordlist']
                        or 'default' in yaml_configuration['subdomain_discovery']['wordlist']):
                    wordlist_location = settings.TOOL_LOCATION + \
                        'wordlist/default_wordlist/deepmagic.com-prefixes-top50000.txt'
                else:
                    wordlist_location = settings.TOOL_LOCATION + 'wordlist/' + \
                        yaml_configuration['subdomain_discovery']['wordlist'] + '.txt'
                    if not os.path.exists(wordlist_location):
                        wordlist_location = settings.TOOL_LOCATION + \
                            'wordlist/default_wordlist/deepmagic.com-prefixes-top50000.txt'
                # check if default amass config is to be used
                if ('amass_config' not in yaml_configuration['subdomain_discovery']
                    or not yaml_configuration['subdomain_discovery']['amass_config']
                        or 'default' in yaml_configuration['subdomain_discovery']['wordlist']):
                    amass_config = settings.AMASS_CONFIG
                else:
                    '''
                    amass config setting exixts but we need to check if it
                    exists in database
                    '''
                    short_name = yaml_configuration['subdomain_discovery']['amass_config']
                    config = get_object_or_404(
                        Configuration, short_name=short_name)
                    if config:
                        '''
                        if config exists in db then write the config to
                        scan location, and send path to script location
                        '''
                        with open(current_scan_dir + '/config.ini', 'w') as config_file:
                            config_file.write(config.content)
                        amass_config = current_scan_dir + '/config.ini'
                    else:
                        '''
                        if config does not exist in db then
                        use default for failsafe
                        '''
                        amass_config = settings.AMASS_CONFIG

                # all subdomain scan happens here
                os.system(
                    settings.TOOL_LOCATION +
                    'get_subdomain.sh %s %s %s %s %s %s' %
                    (threads,
                     domain.domain_name,
                     current_scan_dir,
                     wordlist_location,
                     amass_config,
                     tools))
            else:
                os.system(
                    settings.TOOL_LOCATION + 'get_subdomain.sh %s %s %s %s' %
                    (threads, domain.domain_name, current_scan_dir, tools))

            subdomain_scan_results_file = results_dir + \
                current_scan_dir + '/sorted_subdomain_collection.txt'

            with open(subdomain_scan_results_file) as subdomain_list:
                for subdomain in subdomain_list:
                    scanned = ScannedHost()
                    scanned.subdomain = subdomain.rstrip('\n')
                    scanned.scan_history = task
                    scanned.save()
        else:
            only_subdomain_file = open(
                results_dir +
                current_scan_dir +
                '/sorted_subdomain_collection.txt',
                "w")
            only_subdomain_file.write(domain.domain_name + "\n")
            only_subdomain_file.close()

            scanned = ScannedHost()
            scanned.subdomain = domain.domain_name
            scanned.scan_history = task
            scanned.save()

        subdomain_scan_results_file = results_dir + \
            current_scan_dir + '/sorted_subdomain_collection.txt'

        if(task.scan_type.port_scan):
            update_last_activity()
            create_scan_activity(task, "Port Scanning", 1)

            # after all subdomain has been discovered run naabu to discover the
            # ports
            port_results_file = results_dir + current_scan_dir + '/ports.json'

            # check the yaml_configuration and choose the ports to be scanned

            scan_ports = ','.join(
                str(port) for port in yaml_configuration['port_scan']['ports'])

            if scan_ports:
                naabu_command = 'cat {} | naabu -json -o {} -ports {}'.format(
                    subdomain_scan_results_file, port_results_file, scan_ports)
            else:
                naabu_command = 'cat {} | naabu -json -o {}'.format(
                    subdomain_scan_results_file, port_results_file)

            # check for exclude ports

            if yaml_configuration['port_scan']['exclude_ports']:
                exclude_ports = ','.join(
                    str(port) for port in yaml_configuration['port_scan']['exclude_ports'])
                naabu_command = naabu_command + \
                    ' -exclude-ports {}'.format(exclude_ports)

            if yaml_configuration['subdomain_discovery']['thread'] > 0:
                naabu_command = naabu_command + \
                    ' -t {}'.format(
                        yaml_configuration['subdomain_discovery']['thread'])
            else:
                naabu_command = naabu_command + ' -t 10'

            # run naabu
            os.system(naabu_command)

            # writing port results
            try:
                port_json_result = open(port_results_file, 'r')
                lines = port_json_result.readlines()
                for line in lines:
                    try:
                        json_st = json.loads(line.strip())
                    except BaseException:
                        json_st = "{'host':'','port':''}"
                    sub_domain = ScannedHost.objects.get(
                        scan_history=task, subdomain=json_st['host'])
                    if sub_domain.open_ports:
                        sub_domain.open_ports = sub_domain.open_ports + \
                            ',' + str(json_st['port'])
                    else:
                        sub_domain.open_ports = str(json_st['port'])
                    sub_domain.save()
            except BaseException:
                print('No Ports file')

        '''
        HTTP Crawlwer and screenshot will run by default
        '''
        update_last_activity()
        create_scan_activity(task, "HTTP Crawler", 1)

        # once port scan is complete then run httpx, TODO this has to run in
        # background thread later
        httpx_results_file = results_dir + current_scan_dir + '/httpx.json'

        httpx_command = 'cat {} | httpx -json -o {}'.format(
            subdomain_scan_results_file, httpx_results_file)
        os.system(httpx_command)

        # alive subdomains from httpx
        alive_file_location = results_dir + current_scan_dir + '/alive.txt'
        alive_file = open(alive_file_location, 'w')

        # writing httpx results
        httpx_json_result = open(httpx_results_file, 'r')
        lines = httpx_json_result.readlines()
        for line in lines:
            json_st = json.loads(line.strip())
            sub_domain = ScannedHost.objects.get(
                scan_history=task, subdomain=json_st['url'].split("//")[-1])
            sub_domain.http_url = json_st['url']
            sub_domain.http_status = json_st['status-code']
            sub_domain.page_title = json_st['title']
            sub_domain.content_length = json_st['content-length']
            alive_file.write(json_st['url'] + '\n')
            sub_domain.save()
        alive_file.close()

        update_last_activity()
        create_scan_activity(task, "Visual Recon - Screenshot", 1)

        # after subdomain discovery run aquatone for visual identification
        with_protocol_path = results_dir + current_scan_dir + '/alive.txt'
        output_aquatone_path = results_dir + current_scan_dir + '/aquascreenshots'

        scan_port = yaml_configuration['visual_identification']['port']
        # check if scan port is valid otherwise proceed with default xlarge
        # port
        if scan_port not in ['small', 'medium', 'large', 'xlarge']:
            scan_port = 'xlarge'

        if yaml_configuration['visual_identification']['thread'] > 0:
            threads = yaml_configuration['visual_identification']['thread']
        else:
            threads = 10

        aquatone_command = 'cat {} | /app/tools/aquatone --threads {} -ports {} -out {}'.format(
            with_protocol_path, threads, scan_port, output_aquatone_path)
        os.system(aquatone_command)
        os.system('chmod -R 607 /app/tools/scan_results/*')
        aqua_json_path = output_aquatone_path + '/aquatone_session.json'
        with open(aqua_json_path, 'r') as json_file:
            data = json.load(json_file)

        for host in data['pages']:
            sub_domain = ScannedHost.objects.get(
                scan_history__id=host_id,
                subdomain=data['pages'][host]['hostname'])
            list_ip = data['pages'][host]['addrs']
            ip_string = ','.join(list_ip)
            sub_domain.ip_address = ip_string
            sub_domain.screenshot_path = current_scan_dir + \
                '/aquascreenshots/' + data['pages'][host]['screenshotPath']
            sub_domain.http_header_path = current_scan_dir + \
                '/aquascreenshots/' + data['pages'][host]['headersPath']
            tech_list = []
            if data['pages'][host]['tags'] is not None:
                for tag in data['pages'][host]['tags']:
                    tech_list.append(tag['text'])
            tech_string = ','.join(tech_list)
            sub_domain.technology_stack = tech_string
            sub_domain.save()

        '''
        Subdomain takeover is not provided by default, check for conditions
        '''
        if(task.scan_type.subdomain_takeover):
            update_last_activity()
            create_scan_activity(task, "Subdomain takeover", 1)

            if yaml_configuration['subdomain_takeover']['thread'] > 0:
                threads = yaml_configuration['subdomain_takeover']['thread']
            else:
                threads = 10

            subjack_command = settings.TOOL_LOCATION + \
                'takeover.sh {} {}'.format(current_scan_dir, threads)

            os.system(subjack_command)

            takeover_results_file = results_dir + current_scan_dir + '/takeover_result.json'

            try:
                with open(takeover_results_file) as f:
                    takeover_data = json.load(f)

                for data in takeover_data:
                    if data['vulnerable']:
                        get_subdomain = ScannedHost.objects.get(
                            scan_history=task, subdomain=subdomain)
                        get_subdomain.takeover = vulnerable_service
                        get_subdomain.save()
                    # else:
                    #     subdomain = data['subdomain']
                    #     get_subdomain = ScannedHost.objects.get(scan_history=task, subdomain=subdomain)
                    #     get_subdomain.takeover = "Debug"
                    #     get_subdomain.save()

            except Exception as e:
                print(e)

        '''
        Directory search is not provided by default, check for conditions
        '''
        if(task.scan_type.dir_file_search):
            update_last_activity()
            create_scan_activity(task, "Directory Search", 1)
            # scan directories for all the alive subdomain with http status >
            # 200
            alive_subdomains = ScannedHost.objects.filter(
                scan_history__id=host_id).exclude(http_url='')
            dirs_results = current_scan_dir + '/dirs.json'

            # check the yaml settings
            extensions = ','.join(
                str(port) for port in yaml_configuration['dir_file_search']['extensions'])

            # find the threads from yaml
            if yaml_configuration['dir_file_search']['thread'] > 0:
                threads = yaml_configuration['dir_file_search']['thread']
            else:
                threads = 10

            for subdomain in alive_subdomains:
                # /app/tools/dirsearch/db/dicc.txt
                if ('wordlist' not in yaml_configuration['dir_file_search'] or
                    not yaml_configuration['dir_file_search']['wordlist'] or
                        'default' in yaml_configuration['dir_file_search']['wordlist']):
                    wordlist_location = settings.TOOL_LOCATION + 'dirsearch/db/dicc.txt'
                else:
                    wordlist_location = settings.TOOL_LOCATION + 'wordlist/' + \
                        yaml_configuration['dir_file_search']['wordlist'] + '.txt'

                dirsearch_command = settings.TOOL_LOCATION + 'get_dirs.sh {} {} {}'.format(
                    subdomain.http_url, wordlist_location, dirs_results)
                dirsearch_command = dirsearch_command + \
                    ' {} {}'.format(extensions, threads)

                # check if recursive strategy is set to on
                if yaml_configuration['dir_file_search']['recursive']:
                    dirsearch_command = dirsearch_command + \
                        ' {}'.format(
                            yaml_configuration['dir_file_search']['recursive_level'])

                os.system(dirsearch_command)
                try:
                    with open(dirs_results, "r") as json_file:
                        json_string = json_file.read()
                        scanned_host = ScannedHost.objects.get(
                            scan_history__id=host_id, http_url=subdomain.http_url)
                        scanned_host.directory_json = json_string
                        scanned_host.save()
                except BaseException:
                    print("No File")

        '''
        Getting endpoint from GAU, is also not set by default, check for conditions.
        One thing to change is that, currently in gau, providers is set to wayback,
        later give them choice
        '''
        # TODO: give providers as choice for users between commoncrawl,
        # alienvault or wayback
        if(task.scan_type.fetch_url):
            update_last_activity()
            create_scan_activity(task, "Fetching endpoints", 1)
            wayback_results_file = results_dir + current_scan_dir + '/url_wayback.json'

            '''
            It first runs gau to gather all urls from wayback, then we will use hakrawler to identify more urls
            '''
            # check yaml settings
            if 'all' in yaml_configuration['fetch_url']['uses_tool']:
                tools = 'gau hakrawler'
            else:
                tools = ' '.join(
                    str(tool) for tool in yaml_configuration['fetch_url']['uses_tool'])

            os.system(
                settings.TOOL_LOCATION + 'get_urls.sh %s %s %s' %
                (domain.domain_name, current_scan_dir, tools))

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
    scan_status_msg = {
        'text': "reEngine finished scanning " + domain.domain_name}
    headers = {'content-type': 'application/json'}
    for notif in notif_hook:
        requests.post(
            notif.hook_url,
            data=json.dumps(scan_status_msg),
            headers=headers)
    update_last_activity()
    create_scan_activity(task, "Scan Completed", 2)
    return {"status": True}


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
    # save the last activity as successful
    last_activity = ScanActivity.objects.latest('id')
    last_activity.status = 2
    last_activity.time = timezone.now()
    last_activity.save()

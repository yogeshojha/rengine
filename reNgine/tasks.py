import os
import traceback
import yaml
import json
import validators
import requests
import logging
import whatportis

from celery import shared_task
from discord_webhook import DiscordWebhook
from reNgine.celery import app
from startScan.models import *
from targetApp.models import Domain
from scanEngine.models import EngineType
from django.conf import settings
from django.utils import timezone, dateformat
from django.shortcuts import get_object_or_404

from celery import shared_task
from datetime import datetime

from django.conf import settings
from django.utils import timezone, dateformat
from django.shortcuts import get_object_or_404
from django.core.exceptions import ObjectDoesNotExist

from reNgine.celery import app
from reNgine.definitions import *

from startScan.models import *
from targetApp.models import Domain
from scanEngine.models import EngineType, Configuration, Wordlist

from .common_func import *

'''
task for background scan
'''


@app.task
def initiate_scan(
        domain_id,
        scan_history_id,
        scan_type,
        engine_type,
        imported_subdomains=None):
    '''
    scan_type = 0 -> immediate scan, need not create scan object
    scan_type = 1 -> scheduled scan
    '''
    engine_object = EngineType.objects.get(pk=engine_type)
    domain = Domain.objects.get(pk=domain_id)
    if scan_type == 1:
        task = ScanHistory()
        task.scan_status = -1
    elif scan_type == 0:
        task = ScanHistory.objects.get(pk=scan_history_id)

    # save the last scan date for domain model
    domain.last_scan_date = timezone.now()
    domain.save()

    # once the celery task starts, change the task status to Started
    task.scan_type = engine_object
    task.celery_id = initiate_scan.request.id
    task.domain = domain
    task.scan_status = 1
    task.start_scan_date = timezone.now()
    task.subdomain_discovery = True if engine_object.subdomain_discovery else False
    task.dir_file_search = True if engine_object.dir_file_search else False
    task.port_scan = True if engine_object.port_scan else False
    task.fetch_url = True if engine_object.fetch_url else False
    task.vulnerability_scan = True if engine_object.vulnerability_scan else False
    task.save()

    activity_id = create_scan_activity(task, "Scanning Started", 2)
    results_dir = settings.TOOL_LOCATION + 'scan_results/'
    os.chdir(results_dir)

    try:
        current_scan_dir = domain.name + '_' + \
            str(datetime.datetime.strftime(timezone.now(), '%Y_%m_%d_%H_%M_%S'))
        os.mkdir(current_scan_dir)
    except Exception as exception:
        logger.error(exception)
        scan_failed(task)

    yaml_configuration = None
    excluded_subdomains = ''

    try:
        yaml_configuration = yaml.load(
            task.scan_type.yaml_configuration,
            Loader=yaml.FullLoader)
    except Exception as exception:
        logger.error(exception)
        # TODO: Put failed reason on db

    '''
    Add GF patterns name to db for dynamic URLs menu
    '''
    task.used_gf_patterns = ','.join(
        pattern for pattern in yaml_configuration[FETCH_URL][GF_PATTERNS]) if engine_object.fetch_url else None
    task.save()

    results_dir = results_dir + current_scan_dir

    # put all imported subdomains into txt file and also in Subdomain model
    if imported_subdomains:
        extract_imported_subdomain(
            imported_subdomains, task, domain, results_dir)

    if yaml_configuration:
        '''
        a target in itself is a subdomain, some tool give subdomains as
        www.yogeshojha.com but url and everything else resolves to yogeshojha.com
        In that case, we would already need to store target itself as subdomain
        '''

        initial_subdomain_file = '/target_domain.txt' if task.subdomain_discovery else '/sorted_subdomain_collection.txt'

        subdomain_file = open(results_dir + initial_subdomain_file, "w")
        subdomain_file.write(domain.name + "\n")
        subdomain_file.close()

        if(task.subdomain_discovery):
            activity_id = create_scan_activity(task, "Subdomain Scanning", 1)
            subdomain_scan(
                task,
                domain,
                yaml_configuration,
                results_dir,
                activity_id)
        else:
            skip_subdomain_scan(task, domain, results_dir)

        update_last_activity(activity_id, 2)
        activity_id = create_scan_activity(task, "HTTP Crawler", 1)
        http_crawler(
            task,
            domain,
            results_dir,
            activity_id)
        update_last_activity(activity_id, 2)

        if VISUAL_IDENTIFICATION in yaml_configuration:
            activity_id = create_scan_activity(
                task, "Visual Recon - Screenshot", 1)
            grab_screenshot(
                task,
                yaml_configuration,
                current_scan_dir,
                activity_id)
            update_last_activity(activity_id, 2)

        if(task.port_scan):
            activity_id = create_scan_activity(task, "Port Scanning", 1)
            port_scanning(task, domain, yaml_configuration, results_dir)
            update_last_activity(activity_id, 2)

        if(task.dir_file_search):
            activity_id = create_scan_activity(task, "Directory Search", 1)
            directory_brute(task, yaml_configuration, results_dir, activity_id)
            update_last_activity(activity_id, 2)

        if(task.fetch_url):
            activity_id = create_scan_activity(task, "Fetching endpoints", 1)
            fetch_endpoints(
                task,
                domain,
                yaml_configuration,
                results_dir,
                activity_id)
            update_last_activity(activity_id, 2)

        if(task.vulnerability_scan):
            activity_id = create_scan_activity(task, "Vulnerability Scan", 1)
            vulnerability_scan(
                task,
                domain,
                yaml_configuration,
                results_dir,
                activity_id)
            update_last_activity(activity_id, 2)

    activity_id = create_scan_activity(task, "Scan Completed", 2)

    '''
    Once the scan is completed, save the status to successful
    '''
    if ScanActivity.objects.filter(scan_of=task).filter(status=0).all():
        task.scan_status = 0
    else:
        task.scan_status = 2
    task.stop_scan_date = timezone.now()
    task.save()
    # cleanup results
    # delete_scan_data(results_dir)
    return {"status": True}


def skip_subdomain_scan(task, domain, results_dir):
    # store default target as subdomain
    '''
    If the imported subdomain already has target domain saved, we can skip this
    '''
    if not Subdomain.objects.filter(
            scan_history=task,
            name=domain.name).exists():
        scanned = Subdomain()
        scanned.name = domain.name
        scanned.scan_history = task
        scanned.target_domain = domain
        scanned.save()

    # Save target into target_domain.txt
    with open('{}/target_domain.txt'.format(results_dir), 'w+') as file:
        file.write(domain.name + '\n')

    file.close()

    '''
    We can have two conditions, either subdomain scan happens, or subdomain scan
    does not happen, in either cases, because we are using import subdomain, we
    need to collect and sort all the subdomains

    Write target domain into subdomain_collection
    '''

    os.system(
        'cat {0}/target_domain.txt > {0}/subdomain_collection.txt'.format(results_dir))

    os.system(
        'cat {0}/from_imported.txt > {0}/subdomain_collection.txt'.format(results_dir))

    os.system('rm -f {}/from_imported.txt'.format(results_dir))

    '''
    Sort all Subdomains
    '''
    os.system(
        'sort -u {0}/subdomain_collection.txt -o {0}/sorted_subdomain_collection.txt'.format(results_dir))

    os.system('rm -f {}/subdomain_collection.txt'.format(results_dir))


def extract_imported_subdomain(imported_subdomains, task, domain, results_dir):
    valid_imported_subdomains = [subdomain for subdomain in imported_subdomains if validators.domain(
        subdomain) and domain.name == get_domain_from_subdomain(subdomain)]

    # remove any duplicate
    valid_imported_subdomains = list(set(valid_imported_subdomains))

    with open('{}/from_imported.txt'.format(results_dir), 'w+') as file:
        for _subdomain in valid_imported_subdomains:
            # save _subdomain to Subdomain model db
            if not Subdomain.objects.filter(
                    scan_history=task, name=_subdomain).exists():
                subdomain = Subdomain()
                subdomain.scan_history = task
                subdomain.target_domain = domain
                subdomain.name = _subdomain
                subdomain.is_imported_subdomain = True
                subdomain.save()
                # save subdomain to file
                file.write('{}\n'.format(_subdomain))

    file.close()


def subdomain_scan(task, domain, yaml_configuration, results_dir, activity_id):
    '''
    This function is responsible for performing subdomain enumeration
    '''
    subdomain_scan_results_file = results_dir + '/sorted_subdomain_collection.txt'
    # Excluded subdomains
    excluded_subdomains = ''
    if EXCLUDED_SUBDOMAINS in yaml_configuration:
        excluded_subdomains = yaml_configuration[EXCLUDED_SUBDOMAINS]

    # check for all the tools and add them into string
    # if tool selected is all then make string, no need for loop
    if ALL in yaml_configuration[SUBDOMAIN_DISCOVERY][USES_TOOLS]:
        tools = 'amass-active amass-passive assetfinder sublist3r subfinder oneforall'
    else:
        tools = ' '.join(
            str(tool) for tool in yaml_configuration[SUBDOMAIN_DISCOVERY][USES_TOOLS])

    logging.info(tools)

    # check for thread, by default 10
    threads = 10
    if THREAD in yaml_configuration[SUBDOMAIN_DISCOVERY]:
        _threads = yaml_configuration[SUBDOMAIN_DISCOVERY][THREAD]
        if _threads > 0:
            threads = _threads

    if 'amass' in tools:
        amass_config_path = None
        if AMASS_CONFIG in yaml_configuration[SUBDOMAIN_DISCOVERY]:
            short_name = yaml_configuration[SUBDOMAIN_DISCOVERY][AMASS_CONFIG]
            try:
                config = get_object_or_404(
                    Configuration, short_name=short_name)
                '''
                if config exists in db then write the config to
                scan location, and append in amass_command
                '''
                with open(results_dir + '/config.ini', 'w') as config_file:
                    config_file.write(config.content)
                amass_config_path = results_dir + '/config.ini'
            except Exception as e:
                logging.error(CONFIG_FILE_NOT_FOUND)
                pass

        if 'amass-passive' in tools:
            amass_command = AMASS_COMMAND + \
                ' -passive -d {} -o {}/from_amass.txt'.format(
                    domain.name, results_dir)
            if amass_config_path:
                amass_command = amass_command + \
                    ' -config {}'.format(settings.TOOL_LOCATION +
                                         'scan_results/' + amass_config_path)

            # Run Amass Passive
            logging.info(amass_command)
            os.system(amass_command)

        if 'amass-active' in tools:
            amass_command = AMASS_COMMAND + \
                ' -active -d {} -o {}/from_amass_active.txt'.format(
                    domain.name, results_dir)

            if AMASS_WORDLIST in yaml_configuration[SUBDOMAIN_DISCOVERY]:
                wordlist = yaml_configuration[SUBDOMAIN_DISCOVERY][AMASS_WORDLIST]
                if wordlist == 'default':
                    wordlist_path = settings.TOOL_LOCATION + AMASS_DEFAULT_WORDLIST_PATH
                else:
                    wordlist_path = settings.TOOL_LOCATION + 'wordlist/' + wordlist + '.txt'
                    if not os.path.exists(wordlist_path):
                        wordlist_path = settings.TOOL_LOCATION + AMASS_WORDLIST
                amass_command = amass_command + \
                    ' -brute -w {}'.format(wordlist_path)
            if amass_config_path:
                amass_command = amass_command + \
                    ' -config {}'.format(settings.TOOL_LOCATION +
                                         'scan_results/' + amass_config_path)

            # Run Amass Active
            logging.info(amass_command)
            os.system(amass_command)

    if 'assetfinder' in tools:
        assetfinder_command = 'assetfinder --subs-only {} > {}/from_assetfinder.txt'.format(
            domain.name, results_dir)

        # Run Assetfinder
        logging.info(assetfinder_command)
        os.system(assetfinder_command)

    if 'sublist3r' in tools:
        sublist3r_command = 'python3 /app/tools/Sublist3r/sublist3r.py -d {} -t {} -o {}/from_sublister.txt'.format(
            domain.name, threads, results_dir)

        # Run sublist3r
        logging.info(sublist3r_command)
        os.system(sublist3r_command)

    if 'subfinder' in tools:
        subfinder_command = 'subfinder -d {} -t {} -o {}/from_subfinder.txt'.format(
            domain.name, threads, results_dir)

        # Check for Subfinder config files
        if SUBFINDER_CONFIG in yaml_configuration[SUBDOMAIN_DISCOVERY]:
            short_name = yaml_configuration[SUBDOMAIN_DISCOVERY][SUBFINDER_CONFIG]
            try:
                config = get_object_or_404(
                    Configuration, short_name=short_name)
                '''
                if config exists in db then write the config to
                scan location, and append in amass_command
                '''
                with open(results_dir + '/subfinder-config.yaml', 'w') as config_file:
                    config_file.write(config.content)
                subfinder_config_path = results_dir + '/subfinder-config.yaml'
            except Exception as e:
                pass
            subfinder_command = subfinder_command + \
                ' -config {}'.format(subfinder_config_path)

        # Run Subfinder
        logging.info(subfinder_command)
        os.system(subfinder_command)

    if 'oneforall' in tools:
        oneforall_command = 'python3 /app/tools/OneForAll/oneforall.py --target {} run'.format(
            domain.name, results_dir)

        # Run OneForAll
        logging.info(oneforall_command)
        os.system(oneforall_command)

        extract_subdomain = "cut -d',' -f6 /app/tools/OneForAll/results/{}.csv >> {}/from_oneforall.txt".format(
            domain.name, results_dir)

        os.system(extract_subdomain)

        # remove the results from oneforall directory
        os.system(
            'rm -rf /app/tools/OneForAll/results/{}.*'.format(domain.name))

    '''
    All tools have gathered the list of subdomains with filename
    initials as from_*
    We will gather all the results in one single file, sort them and
    remove the older results from_*
    '''
    os.system(
        'cat {0}/*.txt > {0}/subdomain_collection.txt'.format(results_dir))

    '''
    Write target domain into subdomain_collection
    '''
    os.system(
        'cat {0}/target_domain.txt >> {0}/subdomain_collection.txt'.format(results_dir))

    '''
    Remove all the from_* files
    '''
    os.system('rm -f {}/from*'.format(results_dir))

    '''
    Sort all Subdomains
    '''
    os.system(
        'sort -u {0}/subdomain_collection.txt -o {0}/sorted_subdomain_collection.txt'.format(results_dir))

    os.system('rm -f {}/subdomain_collection.txt'.format(results_dir))

    '''
    The final results will be stored in sorted_subdomain_collection.
    '''
    # parse the subdomain list file and store in db
    with open(subdomain_scan_results_file) as subdomain_list:
        for _subdomain in subdomain_list:
            __subdomain = _subdomain.rstrip('\n')
            if not Subdomain.objects.filter(scan_history=task, name=__subdomain).exists(
            ) and validators.domain(__subdomain) and __subdomain not in excluded_subdomains:
                print('Saving {}'.format(__subdomain))
                subdomain = Subdomain()
                subdomain.scan_history = task
                subdomain.target_domain = domain
                subdomain.name = __subdomain
                subdomain.save()


def http_crawler(task, domain, results_dir, activity_id):
    '''
    This function is runs right after subdomain gathering, and gathers important
    like page title, http status, etc
    HTTP Crawler runs by default
    '''
    alive_file_location = results_dir + '/alive.txt'
    httpx_results_file = results_dir + '/httpx.json'

    subdomain_scan_results_file = results_dir + '/sorted_subdomain_collection.txt'

    httpx_command = 'cat {} | httpx -status-code -content-length -title -tech-detect -cdn -ip -follow-host-redirects -random-agent -json -o {}'.format(
        subdomain_scan_results_file, httpx_results_file)

    os.system(httpx_command)

    # alive subdomains from httpx
    alive_file = open(alive_file_location, 'w')

    # writing httpx results
    if os.path.isfile(httpx_results_file):
        httpx_json_result = open(httpx_results_file, 'r')
        lines = httpx_json_result.readlines()
        for line in lines:
            json_st = json.loads(line.strip())
            try:
                subdomain = Subdomain.objects.get(
                    scan_history=task, name=json_st['url'].split("//")[-1])
                '''
                Saving Default http urls to EndPoint
                '''
                endpoint = EndPoint()
                endpoint.scan_history = task
                endpoint.target_domain = domain
                endpoint.subdomain = subdomain
                if 'url' in json_st:
                    endpoint.http_url = json_st['url']
                    subdomain.http_url = json_st['url']
                if 'status-code' in json_st:
                    endpoint.http_status = json_st['status-code']
                    subdomain.http_status = json_st['status-code']
                if 'title' in json_st:
                    endpoint.page_title = json_st['title']
                    subdomain.page_title = json_st['title']
                if 'content-length' in json_st:
                    endpoint.content_length = json_st['content-length']
                    subdomain.content_length = json_st['content-length']
                if 'content-type' in json_st:
                    endpoint.content_type = json_st['content-type']
                    subdomain.content_type = json_st['content-type']
                if 'webserver' in json_st:
                    endpoint.webserver = json_st['webserver']
                    subdomain.webserver = json_st['webserver']
                if 'technologies' in json_st:
                    endpoint.technology_stack = ','.join(
                        json_st['technologies'])
                    subdomain.technology_stack = ','.join(
                        json_st['technologies'])
                if 'response-time' in json_st:
                    response_time = float(
                        ''.join(
                            ch for ch in json_st['response-time'] if not ch.isalpha()))
                    if json_st['response-time'][-2:] == 'ms':
                        response_time = response_time / 1000
                    endpoint.response_time = response_time
                    subdomain.response_time = response_time
                if 'cdn' in json_st:
                    subdomain.is_cdn = json_st['cdn']
                if 'cnames' in json_st:
                    cname_list = ','.join(json_st['cnames'])
                    subdomain.cname = cname_list
                endpoint.discovered_date = timezone.now()
                subdomain.discovered_date = timezone.now()
                endpoint.is_default = True
                endpoint.save()
                subdomain.save()
                if 'a' in json_st:
                    for _ip in json_st['a']:
                        ip = IPAddress()
                        ip.scan_history = task
                        ip.target_domain = domain
                        ip.subdomain = subdomain
                        ip.address = _ip
                        if 'host' in json_st and json_st['host'] == _ip:
                            ip.is_host = True
                        if 'cdn' in json_st:
                            ip.is_cdn = json_st['cdn']
                        ip.save()
                alive_file.write(json_st['url'] + '\n')
            except Exception as exception:
                logging.error(exception)
                update_last_activity(activity_id, 0)
    alive_file.close()


def grab_screenshot(task, yaml_configuration, results_dir, activity_id):
    '''
    This function is responsible for taking screenshots
    '''
    # after subdomain discovery run aquatone for visual identification
    output_aquatone_path = results_dir + '/aquascreenshots'

    alive_subdomains_path = results_dir + '/alive.txt'

    if PORT in yaml_configuration[VISUAL_IDENTIFICATION]:
        scan_port = yaml_configuration[VISUAL_IDENTIFICATION][PORT]
        # check if scan port is valid otherwise proceed with default xlarge
        # port
        if scan_port not in ['small', 'medium', 'large', 'xlarge']:
            scan_port = 'xlarge'
    else:
        scan_port = 'xlarge'

    if THREAD in yaml_configuration[VISUAL_IDENTIFICATION] and yaml_configuration[VISUAL_IDENTIFICATION][THREAD] > 0:
        threads = yaml_configuration[VISUAL_IDENTIFICATION][THREAD]
    else:
        threads = 10

    if HTTP_TIMEOUT in yaml_configuration[VISUAL_IDENTIFICATION]:
        http_timeout = yaml_configuration[VISUAL_IDENTIFICATION][HTTP_TIMEOUT]
    else:
        http_timeout = 3000  # Default Timeout for HTTP

    if SCREENSHOT_TIMEOUT in yaml_configuration[VISUAL_IDENTIFICATION]:
        screenshot_timeout = yaml_configuration[VISUAL_IDENTIFICATION][SCREENSHOT_TIMEOUT]
    else:
        screenshot_timeout = 30000  # Default Timeout for Screenshot

    if SCAN_TIMEOUT in yaml_configuration[VISUAL_IDENTIFICATION]:
        scan_timeout = yaml_configuration[VISUAL_IDENTIFICATION][SCAN_TIMEOUT]
    else:
        scan_timeout = 100  # Default Timeout for Scan

    aquatone_command = 'cat {} | /app/tools/aquatone --threads {} -ports {} -out {} -http-timeout {} -scan-timeout {} -screenshot-timeout {}'.format(
        alive_subdomains_path, threads, scan_port, output_aquatone_path, http_timeout, scan_timeout, screenshot_timeout)

    logging.info(aquatone_command)
    os.system(aquatone_command)
    os.system('chmod -R 607 /app/tools/scan_results/*')
    aqua_json_path = output_aquatone_path + '/aquatone_session.json'

    try:
        if os.path.isfile(aqua_json_path):
            logger.info('Gathering aquatone results')
            with open(aqua_json_path, 'r') as json_file:
                data = json.load(json_file)

            for host in data['pages']:
                try:
                    sub_domain = Subdomain.objects.get(
                        scan_history__id=task.id,
                        name=data['pages'][host]['hostname'])
                    if data['pages'][host]['hasScreenshot']:
                        sub_domain.screenshot_path = results_dir + \
                            '/aquascreenshots/' + data['pages'][host]['screenshotPath']
                        sub_domain.http_header_path = results_dir + \
                            '/aquascreenshots/' + data['pages'][host]['headersPath']
                        sub_domain.save()
                except Exception as e:
                    continue
    except Exception as exception:
        logging.error(exception)
        update_last_activity(activity_id, 0)


def port_scanning(task, domain, yaml_configuration, results_dir):
    '''
    This function is responsible for running the port scan
    '''
    subdomain_scan_results_file = results_dir + '/sorted_subdomain_collection.txt'
    port_results_file = results_dir + '/ports.json'

    # check the yaml_configuration and choose the ports to be scanned

    scan_ports = '-'  # default port scan everything
    if PORTS in yaml_configuration[PORT_SCAN]:
        # TODO:  legacy code, remove top-100 in future versions
        all_ports = yaml_configuration[PORT_SCAN][PORTS]
        if 'full' in all_ports:
            naabu_command = 'cat {} | naabu -json -o {} -p {}'.format(
                subdomain_scan_results_file, port_results_file, '-')
        elif 'top-100' in all_ports:
            naabu_command = 'cat {} | naabu -json -o {} -top-ports 100'.format(
                subdomain_scan_results_file, port_results_file)
        elif 'top-1000' in all_ports:
            naabu_command = 'cat {} | naabu -json -o {} -top-ports 1000'.format(
                subdomain_scan_results_file, port_results_file)
        else:
            scan_ports = ','.join(
                str(port) for port in all_ports)
            naabu_command = 'cat {} | naabu -json -o {} -p {}'.format(
                subdomain_scan_results_file, port_results_file, scan_ports)

    # check for exclude ports
    if EXCLUDE_PORTS in yaml_configuration[PORT_SCAN] and yaml_configuration[PORT_SCAN][EXCLUDE_PORTS]:
        exclude_ports = ','.join(
            str(port) for port in yaml_configuration['port_scan']['exclude_ports'])
        naabu_command = naabu_command + \
            ' -exclude-ports {}'.format(exclude_ports)

    if NAABU_RATE in yaml_configuration[PORT_SCAN] and yaml_configuration[PORT_SCAN][NAABU_RATE] > 0:
        naabu_command = naabu_command + \
            ' -rate {}'.format(
                yaml_configuration[PORT_SCAN][NAABU_RATE])
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
                port = Port()
                port.scan_history = task
                port.target_domain = domain
                sub_domain = Subdomain.objects.get(
                    scan_history=task, name=json_st['host'])
                port.subdomain = sub_domain
                port_number = json_st['port']
                port.number = port_number
                if port_number in UNCOMMON_WEB_PORTS:
                    port.is_uncommon = True

                port_detail = whatportis.get_ports(str(port_number))
                if len(port_detail):
                    port.service_name = port_detail[0].name
                    port.description = port_detail[0].description
                try:
                    if not IPAddress.objects.filter(
                            scan_history=task).filter(
                            subdomain=sub_domain).filter(
                            address=json_st['ip']).exists():
                        # create new ip
                        ip = IPAddress()
                        ip.scan_history = task
                        ip.target_domain = domain
                        ip.subdomain = sub_domain
                        ip.address = json_st['ip']
                        ip.is_host = False
                        ip.is_cdn = False
                        ip.save()
                    ip_address = IPAddress.objects.get(
                        scan_history=task, subdomain=sub_domain, address=json_st['ip'])
                    port.ip = ip_address
                except Exception as e:
                    logger.info(json_st['ip'])
                    logger.info(sub_domain)
                    logger.exception(e)
                    continue
                port.save()
            except Exception as exception:
                logger.exception(exception)
                continue
    except BaseException as exception:
        logging.error(exception)
        update_last_activity(activity_id, 0)


def check_waf():
    '''
    This function will check for the WAF being used in subdomains using wafw00f
    '''
    pass


def directory_brute(task, yaml_configuration, results_dir, activity_id):
    '''
    This function is responsible for performing directory scan
    '''
    # scan directories for all the alive subdomain with http status >
    # 200
    alive_subdomains = Subdomain.objects.filter(
        scan_history__id=task.id).exclude(
        http_url='')
    dirs_results = results_dir + '/dirs.json'

    # check the yaml settings
    if EXTENSIONS in yaml_configuration[DIR_FILE_SEARCH]:
        extensions = ','.join(
            str(port) for port in yaml_configuration[DIR_FILE_SEARCH][EXTENSIONS])
    else:
        extensions = 'php,git,yaml,conf,db,mysql,bak,txt'

    # Threads
    if THREAD in yaml_configuration[DIR_FILE_SEARCH] and yaml_configuration[DIR_FILE_SEARCH][THREAD] > 0:
        threads = yaml_configuration[DIR_FILE_SEARCH][THREAD]
    else:
        threads = 10

    for subdomain in alive_subdomains:
        # /app/tools/dirsearch/db/dicc.txt
        if (WORDLIST not in yaml_configuration[DIR_FILE_SEARCH] or
            not yaml_configuration[DIR_FILE_SEARCH][WORDLIST] or
                'default' in yaml_configuration[DIR_FILE_SEARCH][WORDLIST]):
            wordlist_location = settings.TOOL_LOCATION + 'dirsearch/db/dicc.txt'
        else:
            wordlist_location = settings.TOOL_LOCATION + 'wordlist/' + \
                yaml_configuration[DIR_FILE_SEARCH][WORDLIST] + '.txt'

        dirsearch_command = settings.TOOL_LOCATION + 'get_dirs.sh {} {} {}'.format(
            subdomain.http_url, wordlist_location, dirs_results)
        dirsearch_command = dirsearch_command + \
            ' {} {}'.format(extensions, threads)

        # check if recursive strategy is set to on
        if RECURSIVE in yaml_configuration[DIR_FILE_SEARCH] and yaml_configuration[DIR_FILE_SEARCH][RECURSIVE]:
            dirsearch_command = dirsearch_command + \
                ' {}'.format(
                    yaml_configuration[DIR_FILE_SEARCH][RECURSIVE_LEVEL])

        os.system(dirsearch_command)

        try:
            if os.path.isfile(dirs_results):
                with open(dirs_results, "r") as json_file:
                    json_string = json_file.read()
                    scanned_host = Subdomain.objects.get(
                        scan_history__id=task.id, http_url=subdomain.http_url)
                    scanned_host.directory_json = json_string
                    scanned_host.save()
        except Exception as exception:
            logging.error(exception)
            update_last_activity(activity_id, 0)


def fetch_endpoints(
        task,
        domain,
        yaml_configuration,
        results_dir,
        activity_id):
    '''
    This function is responsible for fetching all the urls associated with target
    and run HTTP probe
    It first runs gau to gather all urls from wayback, then we will use hakrawler to identify more urls
    '''
    # check yaml settings
    if ALL in yaml_configuration[FETCH_URL][USES_TOOLS]:
        tools = 'gauplus hakrawler waybackurls gospider'
    else:
        tools = ' '.join(
            str(tool) for tool in yaml_configuration[FETCH_URL][USES_TOOLS])

    if INTENSITY in yaml_configuration[FETCH_URL]:
        scan_type = yaml_configuration[FETCH_URL][INTENSITY]
    else:
        scan_type = 'normal'

    domain_regex = "\'https?://([a-z0-9]+[.])*{}.*\'".format(domain.name)

    if 'deep' in scan_type:
        # performs deep url gathering for all the subdomains present -
        # RECOMMENDED
        os.system(settings.TOOL_LOCATION + 'get_urls.sh %s %s %s %s %s' %
                  ("None", results_dir, scan_type, domain_regex, tools))
    else:
        # perform url gathering only for main domain - USE only for quick scan
        os.system(
            settings.TOOL_LOCATION +
            'get_urls.sh %s %s %s %s %s' %
            (domain.name,
             results_dir,
             scan_type,
             domain_regex,
             tools))

    if IGNORE_FILE_EXTENSION in yaml_configuration[FETCH_URL]:
        ignore_extension = '|'.join(
            yaml_configuration[FETCH_URL][IGNORE_FILE_EXTENSION])
        logger.info('Ignore extensions' + ignore_extension)
        os.system(
            'cat {0}/all_urls.txt | grep -Eiv "\\.({1}).*" > {0}/temp_urls.txt'.format(
                results_dir, ignore_extension))
        os.system(
            'rm {0}/all_urls.txt && mv {0}/temp_urls.txt {0}/all_urls.txt'.format(results_dir))

    '''
    Go spider & waybackurls accumulates a lot of urls, which is good but nuclei
    takes forever to scan even a simple website, so we will do http probing
    and filter HTTP status 404, this way we can reduce the number of Non Existent
    URLS
    '''
    os.system('httpx -l {0}/all_urls.txt -status-code -content-length -ip -cdn -title -tech-detect -json -follow-redirects -o {0}/final_httpx_urls.json'.format(results_dir))

    url_results_file = results_dir + '/final_httpx_urls.json'
    try:
        urls_json_result = open(url_results_file, 'r')
        lines = urls_json_result.readlines()
        for line in lines:
            json_st = json.loads(line.strip())
            if not EndPoint.objects.filter(
                    scan_history=task).filter(
                    http_url=json_st['url']).count():
                endpoint = EndPoint()
                endpoint.scan_history = task
                endpoint.target_domain = domain
                endpoint.http_url = json_st['url']
                # extract the subdomain from url and map to Subdomain Model
                _subdomain = get_subdomain_from_url(json_st['url'])
                try:
                    subdomain = Subdomain.objects.get(
                        scan_history=task, name=_subdomain)
                except Exception as exception:
                    '''
                    gau or gosppider can gather interesting endpoints which
                    when parsed can give subdomains that were not existent from
                    subdomain scan. so storing them
                    '''
                    logger.error(json_st['url'])
                    logger.error(
                        'Subdomain {} not found, adding...'.format(_subdomain))
                    subdomain = Subdomain()
                    subdomain.name = _subdomain
                    subdomain.target_domain = domain
                    subdomain.scan_history = task
                    subdomain.save()
                finally:
                    endpoint.subdomain = subdomain
                if 'title' in json_st:
                    endpoint.page_title = json_st['title']
                if 'webserver' in json_st:
                    endpoint.webserver = json_st['webserver']
                if 'content-length' in json_st:
                    endpoint.content_length = json_st['content-length']
                if 'content-type' in json_st:
                    endpoint.content_type = json_st['content-type']
                if 'status-code' in json_st:
                    endpoint.http_status = json_st['status-code']
                if 'technologies' in json_st:
                    endpoint.technology_stack = ','.join(
                        json_st['technologies'])
                if 'response-time' in json_st:
                    response_time = float(
                        ''.join(
                            ch for ch in json_st['response-time'] if not ch.isalpha()))
                    if json_st['response-time'][-2:] == 'ms':
                        response_time = response_time / 1000
                    endpoint.response_time = response_time
                if 'a' in json_st:
                    ip_list = ','.join(json_st['a'])
                    endpoint.ip_address = ip_list
                    endpoint.discovered_date = timezone.now()
                endpoint.save()
    except Exception as exception:
        logging.error(exception)
        update_last_activity(activity_id, 0)

    # once endpoint is saved, run gf patterns
    if GF_PATTERNS in yaml_configuration[FETCH_URL]:
        for pattern in yaml_configuration[FETCH_URL][GF_PATTERNS]:
            logger.info('Running GF for {}'.format(pattern))
            gf_output_file_path = '{0}/gf_patterns_{1}.txt'.format(
                results_dir, pattern)
            gf_command = 'cat {0}/all_urls.txt | gf {1} >> {2}'.format(
                results_dir, pattern, gf_output_file_path)
            os.system(gf_command)
            if os.path.exists(gf_output_file_path):
                with open(gf_output_file_path) as gf_output:
                    for line in gf_output:
                        url = line.rstrip('\n')
                        try:
                            endpoint = EndPoint.objects.get(
                                scan_history=task, http_url=url)
                            earlier_pattern = endpoint.matched_gf_patterns
                            new_pattern = earlier_pattern + ',' + pattern if earlier_pattern else pattern
                            endpoint.matched_gf_patterns = new_pattern
                        except Exception as e:
                            # add the url in db
                            logger.error(e)
                            logger.info('Adding URL' + url)
                            endpoint = EndPoint()
                            endpoint.http_url = url
                            endpoint.target_domain = domain
                            endpoint.scan_history = task
                            try:
                                _subdomain = Subdomain.objects.get(
                                    scan_history=task, name=get_subdomain_from_url(url))
                                endpoint.subdomain = _subdomain
                            except Exception as e:
                                continue
                            endpoint.matched_gf_patterns = pattern
                        finally:
                            endpoint.save()


def vulnerability_scan(
        task,
        domain,
        yaml_configuration,
        results_dir,
        activity_id):
    '''
    This function will run nuclei as a vulnerability scanner
    ----
    unfurl the urls to keep only domain and path, this will be sent to vuln scan
    ignore certain file extensions
    Thanks: https://github.com/six2dez/reconftw
    '''
    urls_path = '/alive.txt'
    if task.scan_type.fetch_url:
        os.system('cat {0}/all_urls.txt | grep -Eiv "\\.(eot|jpg|jpeg|gif|css|tif|tiff|png|ttf|otf|woff|woff2|ico|pdf|svg|txt|js|doc|docx)$" | unfurl -u format %s://%d%p >> {0}/unfurl_urls.txt'.format(results_dir))
        os.system(
            'sort -u {0}/unfurl_urls.txt -o {0}/unfurl_urls.txt'.format(results_dir))
        urls_path = '/unfurl_urls.txt'

    vulnerability_result_path = results_dir + '/vulnerability.json'

    vulnerability_scan_input_file = results_dir + urls_path

    nuclei_command = 'nuclei -json -l {} -o {}'.format(
        vulnerability_scan_input_file, vulnerability_result_path)

    '''
    Nuclei Templates
    Either custom template has to be supplied or default template, if neither has
    been supplied then use all templates including custom templates
    '''

    if CUSTOM_NUCLEI_TEMPLATE in yaml_configuration[
            VULNERABILITY_SCAN] or NUCLEI_TEMPLATE in yaml_configuration[VULNERABILITY_SCAN]:
        # check yaml settings for templates
        if NUCLEI_TEMPLATE in yaml_configuration[VULNERABILITY_SCAN]:
            if ALL in yaml_configuration[VULNERABILITY_SCAN][NUCLEI_TEMPLATE]:
                template = NUCLEI_TEMPLATES_PATH
            else:
                _template = ','.join([NUCLEI_TEMPLATES_PATH + str(element)
                                      for element in yaml_configuration[VULNERABILITY_SCAN][NUCLEI_TEMPLATE]])
                template = _template.replace(',', ' -t ')

            # Update nuclei command with templates
            nuclei_command = nuclei_command + ' -t ' + template

        if CUSTOM_NUCLEI_TEMPLATE in yaml_configuration[VULNERABILITY_SCAN]:
            # add .yaml to the custom template extensions
            _template = ','.join(
                [str(element) + '.yaml' for element in yaml_configuration[VULNERABILITY_SCAN][CUSTOM_NUCLEI_TEMPLATE]])
            template = _template.replace(',', ' -t ')
            # Update nuclei command with templates
            nuclei_command = nuclei_command + ' -t ' + template
    else:
        nuclei_command = nuclei_command + ' -t /root/nuclei-templates'

    # check yaml settings for  concurrency
    if NUCLEI_CONCURRENCY in yaml_configuration[VULNERABILITY_SCAN] and yaml_configuration[
            VULNERABILITY_SCAN][NUCLEI_CONCURRENCY] > 0:
        concurrency = yaml_configuration[VULNERABILITY_SCAN][NUCLEI_CONCURRENCY]
        # Update nuclei command with concurrent
        nuclei_command = nuclei_command + ' -c ' + str(concurrency)

    # for severity
    if NUCLEI_SEVERITY in yaml_configuration[VULNERABILITY_SCAN] and ALL not in yaml_configuration[VULNERABILITY_SCAN][NUCLEI_SEVERITY]:
        _severity = ','.join(
            [str(element) for element in yaml_configuration[VULNERABILITY_SCAN][NUCLEI_SEVERITY]])
        severity = _severity.replace(" ", "")
    else:
        severity = "critical, high, medium, low, info"

    # update nuclei templates before running scan
    os.system('nuclei -update-templates')

    for _severity in severity.split(","):
        # delete any existing vulnerability.json file
        if os.path.isfile(vulnerability_result_path):
            os.system('rm {}'.format(vulnerability_result_path))
        # run nuclei
        final_nuclei_command = nuclei_command + ' -severity ' + _severity
        logger.info(final_nuclei_command)

        os.system(final_nuclei_command)
        try:
            if os.path.isfile(vulnerability_result_path):
                urls_json_result = open(vulnerability_result_path, 'r')
                lines = urls_json_result.readlines()
                for line in lines:
                    json_st = json.loads(line.strip())
                    host = json_st['host']
                    _subdomain = get_subdomain_from_url(host)
                    try:
                        subdomain = Subdomain.objects.get(
                            name=_subdomain, scan_history=task)
                        vulnerability = Vulnerability()
                        vulnerability.subdomain = subdomain
                        vulnerability.scan_history = task
                        vulnerability.target_domain = domain
                        try:
                            endpoint = EndPoint.objects.get(
                                scan_history=task, target_domain=domain, http_url=host)
                            vulnerability.endpoint = endpoint
                        except Exception as exception:
                            pass
                        if 'name' in json_st['info']:
                            vulnerability.name = json_st['info']['name']
                        if 'severity' in json_st['info']:
                            if json_st['info']['severity'] == 'info':
                                severity = 0
                            elif json_st['info']['severity'] == 'low':
                                severity = 1
                            elif json_st['info']['severity'] == 'medium':
                                severity = 2
                            elif json_st['info']['severity'] == 'high':
                                severity = 3
                            elif json_st['info']['severity'] == 'critical':
                                severity = 4
                            else:
                                severity = 0
                        else:
                            severity = 0
                        vulnerability.severity = severity
                        if 'tags' in json_st['info']:
                            vulnerability.tags = json_st['info']['tags']
                        if 'description' in json_st['info']:
                            vulnerability.description = json_st['info']['description']
                        if 'reference' in json_st['info']:
                            vulnerability.reference = json_st['info']['reference']
                        if 'matched' in json_st:
                            vulnerability.http_url = json_st['matched']
                        if 'templateID' in json_st:
                            vulnerability.template_used = json_st['templateID']
                        if 'description' in json_st:
                            vulnerability.description = json_st['description']
                        if 'matcher_name' in json_st:
                            vulnerability.matcher_name = json_st['matcher_name']
                        if 'extracted_results' in json_st:
                            vulnerability.extracted_results = json_st['extracted_results']
                        vulnerability.discovered_date = timezone.now()
                        vulnerability.open_status = True
                        vulnerability.save()
                    except ObjectDoesNotExist:
                        logger.error('Object not found')
                        continue

        except Exception as exception:
            logging.error(exception)
            update_last_activity(activity_id, 0)


def scan_failed(task):
    task.scan_status = 0
    task.stop_scan_date = timezone.now()
    task.save()


def create_scan_activity(task, message, status):
    scan_activity = ScanActivity()
    scan_activity.scan_of = task
    scan_activity.title = message
    scan_activity.time = timezone.now()
    scan_activity.status = status
    scan_activity.save()
    return scan_activity.id


def update_last_activity(id, activity_status):
    ScanActivity.objects.filter(
        id=id).update(
        status=activity_status,
        time=timezone.now())


def delete_scan_data(results_dir):
    # remove all txt,html,json files
    os.system('find {} -name "*.txt" -type f -delete'.format(results_dir))
    os.system('find {} -name "*.html" -type f -delete'.format(results_dir))
    os.system('find {} -name "*.json" -type f -delete'.format(results_dir))


@app.task(bind=True)
def test_task(self):
    print('*' * 40)
    print('test task run')
    print('*' * 40)

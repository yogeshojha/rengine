import csv
import json
import os
import random
import subprocess
import time
from datetime import datetime
from time import sleep
from urllib.parse import urlparse

import asyncwhois
import humanize
import validators
import whatportis
import yaml
from celery import chain, chord, group
from celery.result import allow_join_result
from celery.utils.log import get_task_logger
from degoogle import degoogle
from django.db.models import Count
from django.utils import timezone
from dotted_dict import DottedDict
from emailfinder.extractor import (get_emails_from_baidu, get_emails_from_bing,
                                   get_emails_from_google)
from metafinder.extractor import extract_metadata_from_google_search
from reNgine.celery import app
from reNgine.celery_custom_task import RengineTask
from reNgine.common_func import *
from reNgine.definitions import *
from reNgine.settings import *
from scanEngine.models import (EngineType, InstalledExternalTool, Notification,
                               Proxy)
from startScan.models import *
from startScan.models import EndPoint, Subdomain
from targetApp.models import Domain

"""
Celery tasks.
"""

logger = get_task_logger(__name__)


#----------------------#
# Scan / Subscan tasks #
#----------------------#

@app.task
def initiate_scan(
		scan_history_id,
		activity_id,
		domain_id,
		yaml_configuration={},
		engine_id=None,
		results_dir='/usr/src/scan_results',
		scan_type=LIVE_SCAN,
		imported_subdomains=[],
		out_of_scope_subdomains=[],
		url_path=''):
	"""Initiate a new scan.

	Args:
		scan_history (startScan.models.ScanHistory): ScanHistory instance.
		activity_id (int): Activity ID.
		yaml_configuration (dict): YAML configuration.
		results_dir (str): Results directory.
		engine_id (int): Engine ID.
		scan_type (int): Scan type (periodic, live).
		imported_subdomains (list): Imported subdomains.
		out_of_scope_subdomains (list): Out-of-scope subdomains.
		path (str): URL path. Default: ''
	"""

	# Get ScanHistory
	scan = ScanHistory.objects.get(pk=scan_history_id)

	# Get engine
	engine_id = engine_id or scan.scan_type.id # scan history engine_id
	engine = EngineType.objects.get(pk=engine_id)

	# Get YAML config
	config = yaml.safe_load(engine.yaml_configuration)

	# Get domain and set last_scan_date
	domain = Domain.objects.get(pk=domain_id)
	domain.last_scan_date = timezone.now()
	domain.save()

	# Get path filter
	url_path = url_path.rstrip('/').lstrip('/')

	# Create results directory
	timestr = datetime.strftime(timezone.now(), '%Y_%m_%d_%H_%M_%S')
	scan_dirname = f'{domain.name}_{timestr}'
	results_dir = f'{results_dir}/{scan_dirname}'
	os.makedirs(results_dir, exist_ok=True)

	# Send start notif
	notification = Notification.objects.first()
	send_status = notification.send_scan_status_notif if notification else False
	if send_status:
		title = get_scan_title(scan.id)
		url = get_scan_url(scan.id)
		status = 'RUNNING'
		fields = get_scan_fields(engine, scan, status=status)
		msg = f'{title} {status}\n'
		msg += '\n🡆 '.join(
			f'**{key}:** {value}' for key, value in fields.items())
		logger.warning(msg)
		send_notification.delay(
			msg,
			scan_history_id,
			title=title,
			url=url,
			fields=fields)

	# Get or create ScanHistory() object
	if scan_type == LIVE_SCAN: # immediate
		scan = ScanHistory.objects.get(pk=scan_history_id)
		scan.scan_status = RUNNING_TASK
	elif scan_type == SCHEDULED_SCAN: # scheduled
		scan = ScanHistory()
		scan.scan_status = INITIATED_TASK
	scan.scan_type = engine
	scan.celery_ids = [initiate_scan.request.id]
	scan.domain = domain
	scan.start_scan_date = timezone.now()
	scan.tasks = engine.tasks
	scan.results_dir = scan_dirname
	scan.save()

	# Add GF patterns to scan history
	gf_patterns = config.get(GF_PATTERNS, [])
	add_gf_patterns = gf_patterns and 'fetch_url' in engine.tasks
	if add_gf_patterns:
		scan.used_gf_patterns = ','.join(gf_patterns)
		scan.save()

	# Save imported subdomains in DB
	process_imported_subdomains(
		imported_subdomains,
		scan,
		domain,
		results_dir)

	# Create initial subdomain in DB: make a copy of domain as a subdomain so 
	# that other tasks using subdomains can use it.
	subdomain_name = domain.name
	subdomain, _ = save_subdomain(subdomain_name, scan, domain)

	# Create initial endpoints in DB: find domain HTTP endpoint so that HTTP 
	# crawling can start somewhere
	logger.info('Probing initial endpoints ...')
	base_url = f'{domain.name}/{url_path}' if url_path else domain.name
	save_endpoint(base_url, scan, domain, subdomain, results_dir, crawl=True)

	# Initial URL discovery + checker on domain - will create at least 1 endpoint
	ctx = {
		'scan_history_id': scan_history_id,
		'activity_id': DYNAMIC_ID, # activity will be created dynamically
		'engine_id': engine_id,
		'results_dir': results_dir,
		'url_path': url_path,
		'yaml_configuration': config
	}

	# Build Celery tasks, crafted according to the dependency graph below:
	# initiate_scan --> subdomain_discovery --> port_scan --> fetch_url --> dir_file_fuzz
	#					osint 	   		              		  			    vulnerability_scan
	#		 		 						                  				screenshot
	# 		   		 						           		   				waf_detection
	workflow = chain(
		group(
			subdomain_discovery.si(**ctx, description='Discover subdomains'),
			osint.si(**ctx, description='Perform OS Intelligence')
		),
		port_scan.si(**ctx, description='Scan ports'),
		http_crawl.si(**ctx),
		fetch_url.si(**ctx, description='Fetch endpoints'),
		group(
			dir_file_fuzz.si(**ctx, description='Fuzz directories & files'),
			waf_detection.si(**ctx, description='Detect WAFs'),
			vulnerability_scan.si(**ctx, description='Scan vulnerabilities'),
			screenshot.si(**ctx, description='Grab screenshots')
		)
	)

	# Build callback
	callback = report.si(**ctx).set(link_error=[report.si(**ctx)])

	# Run Celery chord
	logger.info(f'Running Celery workflow with {len(workflow.tasks) + 1} tasks')
	task = chain(workflow, callback).on_error(callback).delay()
	scan.celery_ids.append(task.id)
	scan.save()

	return {
		'success': True,
		'task_id': task.id
	}


@app.task
def initiate_subscan(
		scan_history_id,
		activity_id,
		subdomain_id,
		yaml_configuration,
		results_dir='/usr/src/scan_results',
		engine_id=None,
		url_path='',
		scan_type=None):
	# Get Subdomain and ScanHistory
	subdomain = Subdomain.objects.get(pk=subdomain_id)
	domain = subdomain.target_domain
	scan = ScanHistory.objects.get(pk=subdomain.scan_history.id)

	# Get EngineType
	engine_id = engine_id or scan.scan_type.id
	engine = EngineType.objects.get(pk=engine_id)

	# Create scan activity of SubScan Model
	subscan = SubScan(
		start_scan_date=timezone.now(),
		celery_ids=[initiate_subscan.request.id],
		scan_history=scan,
		subdomain=subdomain,
		type=scan_type,
		status=RUNNING_TASK,
		engine=engine)
	subscan.save()

	# Get YAML configuration
	config = yaml.safe_load(engine.yaml_configuration)

	# Create results directory
	results_dir = f'/usr/src/scan_results/{scan.results_dir}/subscans/{subscan.id}'
	if not os.path.exists(results_dir):
		os.makedirs(results_dir, exist_ok=True)

	# Run task
	method = globals().get(scan_type)
	if not method:
		logger.warning(f'Task {scan_type} is not supported by reNgine. Skipping')
		return
	scan.tasks.append(scan_type)
	scan.save()

	# Send start notif
	notification = Notification.objects.first()
	send_status = notification.send_scan_status_notif if notification else False
	if send_status:
		status = 'RUNNING'
		title = get_scan_title(scan.id, subscan.id)
		fields = get_scan_fields(engine, scan, subscan, status=status)
		url = get_scan_url(scan.id, subscan.id)
		msg = f'{title} {status}\n'
		msg += '\n🡆 '.join(
			f'**{key}:** {value}' for key, value in fields.items())
		logger.warning(msg)
		send_notification.delay(
			msg,
			scan_history_id,
			subscan.id,
			url=url,
			title=title,
			fields=fields)

	# Build header
	ctx = {
		'scan_history_id': scan.id,
		'activity_id': DYNAMIC_ID,
		'engine_id': engine_id,
		'subdomain_id': subdomain.id,
		'yaml_configuration': config,
		'results_dir': results_dir,
		'subscan_id': subscan.id,
		'url_path': url_path
	}
	workflow = method.si(**ctx)
	callback = report.si(**ctx).set(link_error=[report.si(**ctx)])

	# Run Celery tasks
	task = chain(workflow, callback).on_error(callback).delay()
	subscan.celery_ids.append(task.id)
	subscan.save()

	return {
		'success': True,
		'task_id': task.id
	}


@app.task
def report(
		scan_history_id,
		activity_id,
		engine_id=None,
		subdomain_id=None,
		subscan_id=None,
		yaml_configuration={},
		url_path='',
		results_dir=None,
		description=None):
	"""Report task running after all other tasks.
	Mark ScanHistory or SubScan object as completed and update with final 
	status. Log run details and send notification.

	Args:
		scan_history (startScan.models.ScanHistory): ScanHistory instance.
		activity_id (int): Activity ID.
		engine_id (int): Engine ID.
		subdomain_id (int): Subdomain ID.
		send_status (bool, optional): Send status notification. Default: False.
		description (str, optional): Task description.
	"""
	# Get domain, engine, scan_history objects
	engine = EngineType.objects.get(pk=engine_id)
	scan = ScanHistory.objects.get(pk=scan_history_id)
	subscan = SubScan.objects.get(pk=subscan_id) if subscan_id else None
	notification = Notification.objects.first()
	send_status = False
	if notification:
		send_status = notification.send_scan_status_notif

	# Get failed tasks and final status
	failed_tasks = (
		ScanActivity.objects
		.filter(scan_of=scan)
		.filter(status=FAILED_TASK)
		.all()
	)
	if subscan:
		celery_ids = subscan.celery_ids
		failed_tasks = [
			task for task in failed_tasks
			if task.id in celery_ids
		]
	failed_tasks_count = len(failed_tasks)
	status = SUCCESS_TASK if failed_tasks_count == 0 else FAILED_TASK
	status_str = 'SUCCESS' if failed_tasks_count == 0 else 'FAILED'

	# Update scan history
	if not subscan: # do not alter scan status if subscans fail
		scan.scan_status = status
	scan.stop_scan_date = timezone.now()
	scan.save()

	if subscan:
		subscan.stop_scan_date = timezone.now()
		subscan.status = status
		subscan.save()

	# Send notif
	title = get_scan_title(scan.id, subscan_id)
	fields = get_scan_fields(engine, scan, subscan, status=status_str, failed_tasks=failed_tasks_count)
	url = get_scan_url(scan.id, subscan_id)
	msg = f'{title} {status_str}\n'
	severity = 'info'
	if subscan:
		msg += f'\n🡆 **Scan ID:{scan.id}**{msg}'
	msg += '\n🡆 '.join(
		f'**{key}:** {value}' for key, value in fields.items())
	if failed_tasks_count > 0:
		fields['Failed tasks'] = failed_tasks_count
		msg += f'\n🡆 **Failed tasks: {failed_tasks_count}'
		severity = 'error'

	logger.warning(msg)

	# Send notif
	if send_status:
		severity = 'error' if failed_tasks_count > 0 else 'success'
		send_notification.delay(
			msg,
			scan_history_id,
			subscan_id,
			title=title,
			url=url,
			severity=severity,
			fields=fields)


#------------------------- #
# Tracked reNgine tasks    #
#--------------------------#

@app.task(base=RengineTask)
def subdomain_discovery(
		scan_history_id,
		activity_id,
		engine_id=None,
		subdomain_id=None,
		yaml_configuration={},
		results_dir=None,
		out_of_scope_subdomains=[],
		url_path='',
		filename='subdomains.txt',
		description=None,
		subscan_id=None):
	"""Uses a set of tools (see DEFAULT_SUBDOMAIN_SCAN_TOOLS) to scan all 
	subdomains associated with a domain.

	Args:
		scan_history (startScan.models.ScanHistory): ScanHistory instance.
		activity_id (int): Activity ID.
		yaml_configuration (dict): YAML configuration.
		results_dir (str): Results directory.
	"""
	scan = ScanHistory.objects.get(pk=scan_history_id)
	subscan = SubScan.objects.get(pk=subscan_id) if subscan_id else None
	subdomain = Subdomain.objects.get(pk=subdomain_id) if subdomain_id else None
	domain = scan.domain
	host = domain.name
	if subdomain:
		host = subdomain.name
	if url_path:
		logger.warning(f'Ignoring subdomains scan as an URL path filter was passed ({url_path}).')
		return

	# Config
	config = yaml_configuration.get(SUBDOMAIN_DISCOVERY) or {}
	output_path = f'{results_dir}/{filename}'
	threads = config.get(THREADS, 0)
	timeout = config.get(TIMEOUT, DEFAULT_REQUEST_TIMEOUT)
	tools = config.get(USES_TOOLS, DEFAULT_SUBDOMAIN_SCAN_TOOLS)
	default_subdomain_tools = [tool.name.lower() for tool in InstalledExternalTool.objects.filter(is_default=True).filter(is_subdomain_gathering=True)]
	custom_subdomain_tools = [tool.name.lower() for tool in InstalledExternalTool.objects.filter(is_default=False).filter(is_subdomain_gathering=True)]
	send_subdomain_changes, send_interesting = False, False
	notification = Notification.objects.first()
	if notification:
		send_subdomain_changes = notification.send_subdomain_changes_notif
		send_interesting = notification.send_interesting_notif

	# Gather tools to run for subdomain scan
	if ALL in tools:
		tools = DEFAULT_SUBDOMAIN_SCAN_TOOLS + custom_subdomain_tools
	tools = [t.lower() for t in tools]

	# Run tools
	for tool in tools:
		try:
			cmd = None
			logger.info(f'Scanning subdomains with {tool}')
			proxy = get_random_proxy()
			if tool in default_subdomain_tools:
				if tool == 'amass-passive':
					cmd = f'amass enum -passive -d {host} -o {results_dir}/subdomains_amass.txt'
					cmd += ' -config /root/.config/amass.ini' if use_amass_config else ''

				elif tool == 'amass-active':
					use_amass_config = config.get(USE_AMASS_CONFIG, False)
					amass_wordlist_name = config.get(AMASS_WORDLIST, 'deepmagic.com-prefixes-top50000')
					wordlist_path = f'/usr/src/wordlist/{amass_wordlist_name}.txt'
					cmd = f'amass enum -active -d {host} -o {results_dir}/subdomains_amass_active.txt'
					cmd += ' -config /root/.config/amass.ini' if use_amass_config else ''
					cmd += f' -brute -w {wordlist_path}'

				elif tool == 'assetfinder':
					cmd = f'assetfinder --subs-only {host} > {results_dir}/subdomains_assetfinder.txt'

				elif tool == 'sublist3r':
					cmd = f'python3 /usr/src/github/Sublist3r/sublist3r.py -d {host} -t {threads} -o {results_dir}/subdomains_sublister.txt'

				elif tool == 'subfinder':
					cmd = f'subfinder -d {host} -o {results_dir}/subdomains_subfinder.txt'
					use_subfinder_config = config.get(USE_SUBFINDER_CONFIG, False)
					cmd += ' -config /root/.config/subfinder/config.yaml' if use_subfinder_config else ''
					cmd += f' -proxy {proxy}' if proxy else ''
					cmd += f' -timeout {timeout}' if timeout else ''
					cmd += f' -t {threads}' if threads else ''

				elif tool == 'oneforall':
					cmd = f'python3 /usr/src/github/OneForAll/oneforall.py --target {host} run'
					cmd_extract = f'cut -d\',\' -f6 /usr/src/github/OneForAll/results/{host}.csv >> {results_dir}/subdomains_oneforall.txt'
					cmd_rm = f'rm -rf /usr/src/github/OneForAll/results/{host}.csv'
					cmd += f' && {cmd_extract} && {cmd_rm}'
				
				run_command(cmd, shell=True, write_filepath=f'{results_dir}/commands.txt')

			elif tool in custom_subdomain_tools:
				tool_query = InstalledExternalTool.objects.filter(name__icontains=tool.lower())
				if not tool_query.exists():
					logger.error(f'Missing {{TARGET}} and {{OUTPUT}} placeholders in {tool} configuration. Skipping.')
					continue
				custom_tool = tool_query.first()
				cmd = custom_tool.subdomain_gathering_command
				if '{TARGET}' in cmd and '{OUTPUT}' in cmd:
					cmd = cmd.replace('{TARGET}', host)
					cmd = cmd.replace('{OUTPUT}', f'{results_dir}/subdomains_{tool}.txt')
					cmd = cmd.replace('{PATH}', custom_tool.github_clone_path) if '{PATH}' in cmd else cmd

				run_command(cmd, shell=True, write_filepath=f'{results_dir}/commands.txt')
			else:
				logger.warning(
					f'Subdomain discovery tool "{tool}" is not supported by reNgine. Skipping.')

		except Exception as e:
			logger.error(
				f'Subdomain discovery tool "{tool}" raised an exception')
			logger.exception(e)

	# Gather all the tools' results in one single file. Write subdomains into 
	# separate files, and sort all subdomains.
	run_command(
		f'cat {results_dir}/subdomains_*.txt > {output_path}',
		shell=True,
		write_filepath=f'{results_dir}/commands.txt')
	run_command(
		f'sort -u {output_path} -o {output_path}',
		shell=True,
		write_filepath=f'{results_dir}/commands.txt')

	with open(output_path) as f:
		lines = f.readlines()

	# Parse the output_file file and store Subdomain and EndPoint objects found
	# in db.
	subdomain_count = 0
	for line in lines:
		subdomain_name = line.strip()
		valid_domain = bool(validators.domain(subdomain_name))
		valid_ip = bool(validators.ipv4(subdomain_name)) or bool(validators.ipv6(subdomain_name))
		valid_url = bool(validators.url(subdomain_name))
		if not (valid_domain or valid_ip or valid_url):
			logger.error(f'Subdomain {subdomain_name} is not a valid domain, IP or URL. Skipping.')
			continue
		if valid_url:
			subdomain_name = urlparse(subdomain_name).netloc

		if subdomain_name in out_of_scope_subdomains:
			logger.error(f'Subdomain {subdomain_name} is out of scope. Skipping.')
			continue

		# Add subdomain
		subdomain, _ = save_subdomain(subdomain_name, scan, domain)
		subdomain_count += 1

		# Add endpoints
		save_endpoint(
			subdomain_name,
			scan,
			domain,
			subdomain,
			results_dir,
			crawl=True,
			subscan=subscan)

	# Send notifications
	if send_subdomain_changes:
		added = get_new_added_subdomain(scan.id, domain.id)
		removed = get_removed_subdomain(scan.id, domain.id)

		if added:
			msg = f'**{added.count()} new subdomains discovered on domain {host}**\n'
			subdomains_str = '\n'.join([f'• `{subdomain}`' for subdomain in added])
			msg += subdomains_str
			send_notification.delay(msg, scan_history_id, subscan_id)

		if removed:
			msg = f'**{removed.count()} subdomains are no longer available on domain {host}**\n'
			subdomains_str = '\n'.join([f'• `{subdomain}`' for subdomain in removed])
			msg += subdomains_str
			send_notification.delay(msg, scan_history_id, subscan_id)

	if send_interesting:
		interesting_subdomains = get_interesting_subdomains(scan.id, domain.id)
		if interesting_subdomains:
			msg = f'**{interesting_subdomains.count()} interesting subdomains found on domain {host}**\n'
			subdomains_str = '\n'.join([f'• `{subdomain}`' for subdomain in interesting_subdomains])
			msg += subdomains_str
			send_notification.delay(msg, scan_history_id, subscan_id)


@app.task(base=RengineTask)
def osint(
		scan_history_id,
		activity_id,
		engine_id=None,
		yaml_configuration={},
		results_dir=None,
		subdomain_id=None,
		url_path='',
		filename='osint.txt',
		description=None,
		subscan_id=None):
	"""Run Open-Source Intelligence tools on selected domain.

	Args:
		scan_history (startScan.models.ScanHistory): ScanHistory instance.
		activity_id (int): Activity ID.
		yaml_configuration (dict): YAML configuration.
		results_dir (str): Results directory.
		description (str, optional): Task description shown in UI.
	"""
	config = yaml_configuration.get(OSINT) or {}
	scan = ScanHistory.objects.get(pk=scan_history_id)
	subscan = SubScan.objects.get(pk=subscan_id) if subscan_id else None
	domain = scan.domain
	output_path = f'{results_dir}/{filename}'
	results = {}
	if 'discover' in config:
		results = osint_discovery(scan, domain, yaml_configuration, results_dir, subscan=subscan)

	if 'dork' in config:
		results['dorks'] = dorking(scan, yaml_configuration)

	with open(output_path, 'w') as f:
		json.dump(results, f, indent=4)

	return results


@app.task(base=RengineTask)
def screenshot(
		scan_history_id,
		activity_id,
		engine_id=None,
		subdomain_id=None,
		yaml_configuration={},
		results_dir=None,
		url_path='',
		filename='Requests.csv', # cannot be changed.
		description=None,
		subscan_id=None):
	"""Uses EyeWitness to gather screenshot of a domain and/or url.

	Args:
		scan_history (startScan.models.ScanHistory): ScanHistory instance.
		activity_id (int): Activity ID.
		yaml_configuration (dict): YAML configuration.
		results_dir (str): Results directory.
		path (str): URL path.
		description (str, optional): Task description shown in UI.
	"""

	# Config
	screenshots_path = f'{results_dir}/screenshots'
	output_path = f'{results_dir}/screenshots/{filename}'
	alive_endpoints_file = f'{results_dir}/endpoints_alive.txt'
	config = yaml_configuration.get(SCREENSHOT) or {}
	timeout = config.get(TIMEOUT, DEFAULT_REQUEST_TIMEOUT)
	threads = config.get(THREADS, 0)
	scan = ScanHistory.objects.get(pk=scan_history_id)
	domain = scan.domain

	# Get alive endpoints to screenshot
	get_http_urls(
		domain,
		subdomain_id=subdomain_id,
		scan_history=scan,
		is_alive=True,
		url_path=url_path,
		write_filepath=alive_endpoints_file)

	# Send start notif
	notification = Notification.objects.first()
	send_output_file = notification.send_scan_output_file if notification else False

	# Run cmd
	cmd = f'python3 /usr/src/github/EyeWitness/Python/EyeWitness.py -f {alive_endpoints_file} -d {screenshots_path} --no-prompt'
	cmd += f' --timeout {timeout}' if timeout > 0 else ''
	cmd += f' --threads {threads}' if threads > 0 else ''
	run_command(cmd, shell=True)
	if not os.path.isfile(output_path):
		logger.error(f'Could not load EyeWitness results at {output_path} for {domain.name}.')
		return

	# Loop through results and save objects in DB
	screenshot_paths = []
	with open(output_path, 'r') as file:
		reader = csv.reader(file)
		for row in reader:
			"Protocol,Port,Domain,Request Status,Screenshot Path, Source Path"
			protocol, port, subdomain_name, status, screenshot_path, source_path = tuple(row)
			logger.info(f'{protocol}:{port}:{subdomain_name}:{status}')
			subdomain_query = (
				Subdomain.objects
				.filter(scan_history__id=scan.id, name=subdomain_name)
			)
			if status == 'Successful' and subdomain_query.exists():
				subdomain = subdomain_query.first()
				if send_output_file:
					screenshot_paths.append(screenshot_path)
				subdomain.screenshot_path = screenshot_path.replace('/usr/src/scan_results/', '')
				subdomain.save()
				logger.warning(f'Added screenshot for {subdomain.name} to DB')

	# Remove all db, html extra files in screenshot results
	run_command('rm -rf {0}/*.csv {0}/*.db {0}/*.js {0}/*.html {0}/*.css'.format(screenshots_path), shell=True)
	run_command(f'rm -rf {screenshots_path}/source', shell=True)

	# Send finish notif
	if send_output_file:
		for path in screenshot_paths:
			title = get_output_file_name(scan_history_id, subscan_id, filename)
			send_file_to_discord.delay(path, title)


@app.task(base=RengineTask)
def port_scan(
		scan_history_id,
		activity_id,
		engine_id=None,
		yaml_configuration={},
		results_dir=None,
		subdomain_id=None,
		url_path='',
		filename='ports.json',
		description=None,
		subscan_id=None):
	"""Run port scan.

	Args:
		scan_history (startScan.models.ScanHistory): ScanHistory instance.
		activity_id (int): Activity ID.
		yaml_configuration (dict): YAML configuration.
		results_dir (str): Results directory.
		path (str): URL path.
		description (str, optional): Task description shown in UI.

	Returns:
		list: List of open ports (dict).
	"""
	scan = ScanHistory.objects.get(pk=scan_history_id)
	subscan = SubScan.objects.get(pk=subscan_id) if subscan_id else None
	domain = scan.domain
	input_file = f'{results_dir}/input_subdomains_port_scan.txt'
	output_file = f'{results_dir}/{filename}'
	proxy = get_random_proxy()

	# Config
	config = yaml_configuration.get(PORT_SCAN) or {}
	exclude_subdomains = config.get('exclude_subdomains', False)
	exclude_ports = config.get(EXCLUDE_PORTS, [])
	ports = config.get(PORTS, NAABU_DEFAULT_PORTS)
	naabu_rate = config.get(NAABU_RATE, 0)
	use_naabu_config = config.get(USE_NAABU_CONFIG, False)
	exclude_ports_str = ','.join(exclude_ports)

	# Get subdomains
	get_subdomains(
		domain,
		subdomain_id=subdomain_id,
		scan_history=scan,
		url_path=url_path,
		write_filepath=input_file,
		exclude_subdomains=exclude_subdomains)

	# Build cmd
	cmd = 'naabu -json -exclude-cdn'
	cmd += f' -list {input_file}'
	if 'full' in ports:
		ports_str = ' -p "-"'
	elif 'top-100' in ports:
		ports_str = ' -top-ports 100'
	elif 'top-1000' in ports:
		ports_str = ' -top-ports 1000'
	else:
		ports_str = ','.join(ports)
		ports_str = f' -p {ports_str}'
	cmd += f' -proxy "{proxy}"' if proxy else ''
	cmd += ' -config /root/.config/naabu/config.yaml' if use_naabu_config else ''
	cmd += f' -rate {naabu_rate}' if naabu_rate > 0 else ''
	cmd += ports_str
	cmd += f' -exclude-ports {exclude_ports_str}' if exclude_ports else ''
	
	# Execute cmd and gather results
	ports = []
	for line in stream_command(cmd, write_filepath=f'{results_dir}/commands.txt'):
		# TODO: Update Celery task status continously
		if not isinstance(line, dict):
			continue
		ports.append(line)
		port_number = line['port']
		ip_address = line['ip']
		host = line.get('host') or ip_address
		if port_number == 0:
			continue
		logger.warning(f'Found opened port {port_number} on {ip_address} ({host})')
		notif = Notification.objects.first()
		if notif and notif.send_scan_status_notif:
			title = get_task_title('port_scan', scan.id, subscan_id)
			fields = {
				'Status': '**RUNNING**',
				'Ports': ', '.join(f'`{port["port"]}`' for port in ports)
			}
			send_notification.delay(
				'',
				scan.id,
				subscan_id,
				title=title,
				fields=fields)

		# Grab subdomain
		subdomain = Subdomain.objects.filter(
			target_domain=domain,
			name=host,
			scan_history=scan
		).first()

		# Add IP DB
		ip, _ = save_ip_address(ip_address, subdomain, subscan=subscan)

		# Add endpoint to DB
		http_url = f'{host}:{port_number}'
		endpoint, _ = save_endpoint(http_url, scan, domain, subdomain, results_dir, crawl=True)

		# Add Port in DB
		port_details = whatportis.get_ports(str(port_number))
		service_name = 'unknown'
		description = ''
		if len(port_details) > 0:
			service_name = port_details[0].name
			description = port_details[0].description
		if endpoint and endpoint.is_alive:
			url = urlparse(http_url)
			service_name = url.scheme
			description = endpoint.page_title
		port, created = Port.objects.get_or_create(
			number=port_number,
			service_name=service_name,
			description=description)
		if created:
			port.is_uncommon = port_number in UNCOMMON_WEB_PORTS
			port.save()
		ip.ports.add(port)
		ip.save()

		if subscan:
			ip.ip_subscan_ids.add(subscan)
			ip.save()

	# Save output to file
	with open(output_file, 'w') as f:
		json.dump(ports, f, indent=4)

	return ports


@app.task(base=RengineTask)
def waf_detection(
		scan_history_id,
		activity_id,
		engine_id=None,
		subdomain_id=None,
		yaml_configuration={},
		results_dir=None,
		url_path='',
		filename='wafw00f.txt',
		description=None,
		subscan_id=None):
	"""
	Uses wafw00f to check for the presence of a WAF.

	Args:
		scan_history (startScan.models.ScanHistory): ScanHistory instance.
		activity_id (int): Activity ID.
		yaml_configuration (dict): YAML configuration.
		results_dir (str): Results directory.
		path (str): URL path.
		description (str, optional): Task description shown in UI.

	Returns:
		list: List of startScan.models.Waf objects.
	"""
	scan = ScanHistory.objects.get(pk=scan_history_id)
	subscan = SubScan.objects.get(pk=subscan_id) if subscan_id else None
	domain = scan.domain
	input_path = f'{results_dir}/input_endpoints_waf_detection.txt'
	output_path = f'{results_dir}/{filename}'

	# Get alive endpoints from DB
	get_http_urls(
		domain,
		subdomain_id=subdomain_id,
		scan_history=scan,
		is_alive=True,
		url_path=url_path,
		write_filepath=input_path)

	cmd = f'wafw00f -i {input_path} -o {output_path}'
	run_command(cmd)
	if not os.path.isfile(output_path):
		logger.error(f'Could not find {output_path}')
		return

	with open(output_path) as file:
		wafs = file.readlines()

	for line in wafs:
		# split by 3 space!
		splitted = line.split('   ')
		# remove all empty strings
		strs = [string for string in splitted if string]
		# 0th pos is url and 1st pos is waf, remove /n from waf
		waf_info = strs[1].strip()
		waf_name = waf_info[:waf_info.find('(')].strip()
		waf_manufacturer = waf_info[waf_info.find('(')+1:waf_info.find(')')].strip()
		http_url = sanitize_url(strs[0].strip())
		if not waf_name or waf_name == 'None':
			continue

		# Add waf to db
		waf, _ = Waf.objects.get_or_create(
			name=waf_name,
			manufacturer=waf_manufacturer
		)
		waf.save()

		# Add waf info to Subdomain in DB
		subdomain_query = Subdomain.objects.filter(scan_history=scan, http_url=http_url)
		if subdomain_query.exists():
			subdomain = subdomain_query.first()
			subdomain.waf.add(waf)
			subdomain.save()

	return wafs

# TODO: stream_command() for dir_file_fuzz
@app.task(base=RengineTask)
def dir_file_fuzz(
		scan_history_id,
		activity_id,
		engine_id=None,
		subdomain_id=None,
		yaml_configuration={},
		results_dir=None,
		url_path='',
		filename='dirs.json',
		description=None,
		subscan_id=None):
	"""Perform directory scan, and currently uses `ffuf` as a default tool.

	Args:
		scan_history (startScan.models.ScanHistory): ScanHistory instance.
		activity_id (int): Activity ID.
		yaml_configuration (dict): YAML configuration.
		results_dir (str): Results directory.
		description (str, optional): Task description shown in UI.
	"""
	scan = ScanHistory.objects.get(pk=scan_history_id)
	subscan = SubScan.objects.get(pk=subscan_id) if subscan_id else None
	domain = scan.domain
	if subdomain_id:
		subdomain = Subdomain.objects.get(pk=subdomain_id)
		host = subdomain.name
	else:
		host = domain.name

	# Config
	cmd = 'ffuf'
	output_path = f'{results_dir}/{filename}'
	config = yaml_configuration[DIR_FILE_FUZZ]
	custom_header = yaml_configuration.get(CUSTOM_HEADER)
	auto_calibration = config.get(AUTO_CALIBRATION, True)
	delay = config.get(DELAY, 0)
	extensions = config.get(EXTENSIONS, [])
	extensions_str = ','.join(map(str, extensions))
	follow_redirect = config.get(FOLLOW_REDIRECT, False)
	max_time = config.get(MAX_TIME, 0)
	match_http_status = config.get(MATCH_HTTP_STATUS, FFUF_DEFAULT_MATCH_HTTP_STATUS)
	mc = ','.join([str(c) for c in match_http_status])
	recursive_level = config.get(RECURSIVE_LEVEL, 1)	
	stop_on_error = config.get(STOP_ON_ERROR, False)
	timeout = config.get(TIMEOUT, DEFAULT_REQUEST_TIMEOUT)
	threads = config.get(THREADS, 0)
	use_extensions = config.get(USE_EXTENSIONS)
	wordlist_name = config.get(WORDLIST, 'dicc')

	# Send start notification
	notification = Notification.objects.first()
	send_status = notification.send_scan_status_notif if notification else False
	send_output_file = notification.send_scan_output_file if notification else False
	msg = f'`dir_file_fuzz` has started for `{host}`'
	logger.warning(msg)
	if send_status:
		send_notification.delay(msg, scan_history_id, subscan_id)

	# Get wordlist
	wordlist_name = 'dicc' if wordlist_name == 'default' else wordlist_name
	wordlist_path = f'/usr/src/wordlist/{wordlist_name}.txt'

	# Build command
	cmd += f' -w {wordlist_path}'
	cmd += f' -e {extensions_str}' if extensions and use_extensions else ''
	cmd += f' -maxtime {max_time}' if max_time > 0 else ''
	cmd += f' -p "{delay}"' if delay > 0 else ''
	cmd += f' -recursion -recursion-depth {recursive_level} ' if recursive_level else ''
	cmd += f' -t {threads}' if threads and threads > 0 else ''
	cmd += f' -timeout {timeout}' if timeout and timeout > 0 else ''
	cmd += ' -se' if stop_on_error else ''
	cmd += ' -fr' if follow_redirect else ''
	cmd += ' -ac' if auto_calibration else ''
	cmd += f' -mc {mc}' if mc else ''
	cmd += f' -H "{custom_header}"' if custom_header else ''

	# Grab subdomains to fuzz
	if subdomain_id:
		subdomains_fuzz = [Subdomain.objects.get(pk=subdomain_id)]
	else:
		subdomains_fuzz = (
			Subdomain.objects
			.filter(scan_history__id=scan.id, http_url__isnull=False)
		)

	# Loop through subdomains and run command
	dirfile_count = 0
	endpoint_count = 0
	urls = []
	all_results = []
	for subdomain in subdomains_fuzz:
		final_cmd = cmd
		subdomain = Subdomain.objects.get(pk=subdomain.id)

		# Delete any existing dirs.json
		if os.path.isfile(output_path):
			run_command(f'rm -rf {output_path}')

		# HTTP URL
		http_url = subdomain.http_url or subdomain.name
		http_url = http_url.rstrip('/')
		if url_path:
			http_url += f'/{url_path}'
		http_url = probe_url(http_url, first=True)
		if not http_url.endswith('/FUZZ'):
			http_url += '/FUZZ'
		logger.info(f'Running ffuf on {http_url} ...')

		# Proxy
		proxy = get_random_proxy()
		if proxy:
			final_cmd += f' -x {proxy}'

		final_cmd += f' -u {http_url} -o {output_path} -of json'

		# Run cmd
		run_command(final_cmd)
		if not os.path.isfile(output_path):
			logger.error(f'Could not read output file "{output_path}"')
			return

		# Get results
		with open(output_path, "r") as f:
			data = json.load(f)
			all_results.append(data)
			results = data.get('results', [])

		# Initialize DirectoryScan object
		directory_scan = DirectoryScan()
		directory_scan.scanned_date = timezone.now()
		directory_scan.command_line = data['commandline']
		directory_scan.save()

		# Loop through results and populate EndPoint and DirectoryFile in DB
		for result in results:
			logger.info(result)
			name = result['input'].get('FUZZ')
			length = result['length']
			status = result['status']
			words = result['words']
			url = result['url']
			lines = result['lines']
			content_type = result['content-type']
			if not name:
				logger.error(f'FUZZ not found for "{url}"')
				continue
			endpoint, created = save_endpoint(
				http_url,
				scan,
				domain,
				subdomain,
				results_dir,
				crawl=False,
				subscan=subscan)
			if created:
				urls.append(endpoint.http_url)
			endpoint.status = status
			endpoint.content_type = content_type
			endpoint.content_length = length
			dfile, created = DirectoryFile.objects.get_or_create(
				name=name,
				length=length,
				words=words,
				lines=lines,
				content_type=content_type,
				url=url)
			if created:
				logger.warning(f'Found new directory or file {url}')
				dirfile_count += 1
			dfile.http_status = status
			dfile.save()
			directory_scan.directory_files.add(dfile)
			directory_scan.save()

		if subscan:
			directory_scan.dir_subscan_ids.add(subscan)

		subdomain.directories.add(directory_scan)
		subdomain.save()

	# Crawl discovered URLs
	http_crawl(
		scan_history_id,
		activity_id,
		engine_id,
		subdomain_id,
		yaml_configuration,
		results_dir,
		urls=urls)

	results_path = f'{results_dir}/{filename}'
	with open(results_path, 'w') as f:
		json.dump(all_results, f, indent=4)

	msg = f"""`dir_file_fuzz` has finished for `{host}`:
	**{dirfile_count} directories & files discovered**
	**{endpoint_count} endpoints discovered**"""
	if send_status:
		send_notification.delay(msg, scan_history_id, subscan_id)
	if send_output_file:
		title = get_output_file_name(scan_history_id, subscan_id, filename)
		send_file_to_discord.delay(results_path, title)


@app.task(base=RengineTask)
def fetch_url(
		scan_history_id,
		activity_id,
		engine_id=None,
		subdomain_id=None,
		yaml_configuration={},
		results_dir=None,
		filename='urls.txt',
		url_path='',
		description=None,
		subscan_id=None):
	"""Fetch URLs using different tools like gauplus, gospider, waybackurls ...

	Args:
		scan_history (startScan.models.ScanHistory): ScanHistory instance.
		activity_id (int): Activity ID.
		subdomain_id (int): Subdomain ID.
		yaml_configuration (dict): YAML configuration.
		results_dir (str): Results directory.
		filename (str): Filename.
		path (str): URL path.
		description (str, optional): Task description shown in UI.
	"""
	scan = ScanHistory.objects.get(pk=scan_history_id)
	subscan = SubScan.objects.get(pk=subscan_id) if subscan_id else None
	domain = scan.domain

	# Config
	config = yaml_configuration.get(FETCH_URL) or {}
	gf_patterns = config.get(GF_PATTERNS, [])
	ignore_file_extension = config.get(IGNORE_FILE_EXTENSION, [])
	intensity = config.get(INTENSITY, DEFAULT_ENDPOINT_SCAN_INTENSITY)
	tools = config.get(USES_TOOLS, DEFAULT_ENDPOINT_SCAN_TOOLS)
	threads = config.get(THREADS, 0)
	custom_header = domain.request_headers or yaml_configuration.get(CUSTOM_HEADER)
	proxy = get_random_proxy()
	input_path = f'{results_dir}/input_endpoints_fetch_url.txt'
	output_path = f'{results_dir}/{filename}'
	exclude_subdomains = config.get('exclude_subdomains', False)

	# Get URLs to scan and save to input file
	get_http_urls(
		domain,
		subdomain_id,
		scan,
		url_path=url_path,
		is_alive=True,
		write_filepath=input_path,
		exclude_subdomains=exclude_subdomains)

	# Combine old gf patterns with new ones
	if gf_patterns:
		scan.used_gf_patterns = ','.join(gf_patterns)
		scan.save()

	# Domain regex
	domain_regex = f"\'https?://([a-z0-9]+[.])*{domain.name}.*\'"

	# Tools cmds
	cmd_map = {
		'gauplus': f'gauplus --random-agent -t {threads}',
		'hakrawler': 'hakrawler -subs -u',
		'waybackurls': 'waybackurls',
		'gospider': f'gospider -S {input_path} --js -d 2 --sitemap --robots -w -r',
	}
	if proxy:
		cmd_map['gauplus'] += f' -p "{proxy}"'
		cmd_map['gospider'] += f' -p {proxy}'
		cmd_map['hakrawler'] += f' -proxy {proxy}'
	if threads > 0:
		cmd_map['gauplus'] += f' -t {threads}'
		cmd_map['gospider'] += f' -t {threads}'
	if custom_header:
		header_string = ';;'.join([
			f'{key}: {value}' for key, value in custom_header.items()
		])
		cmd_map['hakrawler'] += f' -h {header_string}'
		header_flags = [':'.join(h) for h in header_string.split(';;')]
		for flag in header_flags:
			cmd_map['gospider'] += f' -H {flag}'
	cat_input = f'cat {input_path}'
	grep_output = f'grep -Eo {domain_regex}'
	cmd_map = {
		tool: f'{cat_input} | {cmd} | {grep_output} > {results_dir}/urls_{tool}.txt'
		for tool, cmd in cmd_map.items()
	}
	tasks = group(
		run_command.si(cmd, shell=True)
		for tool, cmd in cmd_map.items()
		if tool in tools
	)

	# Cleanup task
	sort_output = [
		f'cat {results_dir}/urls_* > {output_path}',
		f'cat {input_path}/endpoints_alive.txt >> {output_path}',
		f'sort -u {output_path} -o {output_path}',
	]
	if ignore_file_extension:
		ignore_exts = '|'.join(ignore_file_extension)
		grep_ext_filtered_output = [
			f'cat {output_path} | grep -Eiv "\\.({ignore_exts}).*" > {results_dir}/urls_filtered.txt',
			f'mv {results_dir}/urls_filtered.txt {output_path}'
		]
		sort_output.extend(grep_ext_filtered_output)
	cleanup = chain(run_command.si(cmd, shell=True) for cmd in sort_output)
	
	# Run all commands
	task = chord(tasks)(cleanup)
	with allow_join_result():
		task.get()

	# Store all the endpoints and run httpx
	with open(output_path) as f:
		discovered_urls = f.readlines()

	# Some tools can have an URL in the format <URL>] - <PATH> or <URL> - <PATH>, add them 
	# to the final URL list
	urls = []
	for url in discovered_urls:
		url = url.strip()
		urlpath = None
		base_url = None
		if '] ' in url: # found JS scraped endpoint e.g from gospider
			split = tuple(url.split('] '))
			if not len(split) == 2:
				logger.warning(f'URL format not recognized for "{url}". Skipping.')
				continue
			base_url, urlpath = split
			urlpath = urlpath.lstrip('- ')
		elif ' - ' in url: # found JS scraped endpoint e.g from gospider
			base_url, urlpath = tuple(url.split(' - '))

		if base_url and urlpath:
			subdomain = urlparse(base_url)
			url = f'{subdomain.scheme}://{subdomain.netloc}/{url_path}'

		if not validators.url(url):
			logger.warning(f'Invalid URL "{url}". Skipping.')

		urls.append(url)

	# Filter out URLs if a path filter was passed
	if url_path:
		urls = [url for url in urls if url_path in url]

	# Write result to output path
	with open(output_path, 'w') as f:
		f.write('\n'.join(urls))
	logger.warning(f'Found {len(urls)} usable URLs')

	# Crawl discovered URLs
	http_crawl(
		scan_history_id,
		activity_id,
		engine_id,
		subdomain_id,
		yaml_configuration,
		results_dir,
		urls=urls)

	# Run gf patterns on saved endpoints
	# TODO: refactor to Celery workflow
	gf_patterns = config.get(GF_PATTERNS, [])
	urls = []
	for gf_pattern in gf_patterns:
		# TODO: js var is causing issues, removing for now
		if gf_pattern == 'jsvar':
			logger.info('Ignoring jsvar as it is causing issues.')
			continue
		logger.warning(f'Running gf on pattern "{gf_pattern}"')
		output_file = f'{results_dir}/gf_patterns_{gf_pattern}.txt'
		cmd = f'cat {output_path} | gf {gf_pattern} | grep -Eo {domain_regex} >> {output_file}'
		run_command(cmd, shell=True, write_filepath=f'{results_dir}/commands.txt')
		if not os.path.exists(output_file):
			logger.error(f'Could not find GF output file {output_file}. Skipping GF pattern "{gf_pattern}"')
			continue

		# Read output file line by line and 
		with open(output_file, 'r') as f:
			lines = f.readlines()

		# Add endpoints / subdomains to DB
		for url in lines:
			http_url = sanitize_url(url)
			urls.append(http_url)
			subdomain_name = get_subdomain_from_url(http_url)
			subdomain, _ = save_subdomain(subdomain_name, scan, domain)
			endpoint, created = save_endpoint(
				http_url,
				scan, domain,
				subdomain,
				results_dir,
				crawl=False,
				subscan=subscan)
			earlier_pattern = None
			if not created:
				earlier_pattern = endpoint.matched_gf_patterns
			pattern = f'{earlier_pattern},{gf_pattern}' if earlier_pattern else gf_pattern
			endpoint.matched_gf_patterns = pattern
			endpoint.save()

	# Crawl discovered URLs
	http_crawl(
		scan_history_id,
		activity_id,
		engine_id,
		subdomain_id,
		yaml_configuration,
		results_dir,
		urls=urls)


@app.task(base=RengineTask)
def vulnerability_scan(
		scan_history_id,
		activity_id,
		engine_id=None,
		subdomain_id=None,
		yaml_configuration={},
		url_path='',
		results_dir=None,
		filename='vulnerabilities.json',
		description=None,
		subscan_id=None):
	"""
	This function will run nuclei as a vulnerability scanner

	Args:
		scan_history (startScan.models.ScanHistory): ScanHistory instance.
		activity_id (int): Activity ID.
		subdomain_id (int): Subdomain ID.
		yaml_configuration (dict): YAML configuration.
		path (str): URL path.
		results_dir (str): Results directory.
		description (str, optional): Task description shown in UI.

	Notes:
	Unfurl the urls to keep only domain and path, will be sent to vuln scan and
	ignore certain file extensions. Thanks: https://github.com/six2dez/reconftw
	"""
	scan = ScanHistory.objects.get(pk=scan_history_id)
	subscan = SubScan.objects.get(pk=subscan_id) if subscan_id else None
	domain = scan.domain

	# Config
	cmd = 'nuclei -json'
	input_path = f'{results_dir}/input_endpoints_vulnerability_scan.txt'
	output_path = f'{results_dir}/{filename}'
	config = yaml_configuration.get(VULNERABILITY_SCAN) or {}
	custom_header = config.get(CUSTOM_HEADER)
	concurrency = config.get(NUCLEI_CONCURRENCY, 0)
	custom_nuclei_templates = config.get(NUCLEI_CUSTOM_TEMPLATE, None)
	domain = Domain.objects.get(pk=scan.domain.id)
	nuclei_templates = config.get(NUCLEI_TEMPLATE, None)
	proxy = get_random_proxy()
	rate_limit = config.get(RATE_LIMIT, 0)
	retries = config.get(RETRIES, 0)
	severities = config.get(NUCLEI_SEVERITY, NUCLEI_DEFAULT_SEVERITIES)
	severities_str = ','.join(severities)
	intensity = config.get(INTENSITY, 'normal')
	timeout = config.get(TIMEOUT, DEFAULT_REQUEST_TIMEOUT)
	use_nuclei_conf = config.get(USE_NUCLEI_CONFIG, False)
	
	# Get alive endpoints
	endpoints = get_http_urls(
		domain,
		subdomain_id=subdomain_id,
		scan_history=scan,
		is_alive=True,
		ignore_files=True,
		url_path=url_path,
		write_filepath=input_path)
	endpoints_count = len(endpoints)
	if intensity == 'normal': # reduce number of endpoints to scan
		unfurl_path = f'{results_dir}/unfurl_urls.txt'
		run_command(f'cat {input_path} | unfurl -u format %s://%d%p > {unfurl_path}', shell=True)
		run_command(f'sort -u {unfurl_path} -o  {unfurl_path}', shell=True)
		input_path = unfurl_path
		_, out, _ = run_command(f'cat {unfurl_path} | wc -l', shell=True)
		endpoints_count = int(out)

	# Send start notification
	notification = Notification.objects.first()
	send_vuln = notification.send_vuln_notif if notification else False
	send_status = notification.send_scan_status_notif if notification else False
	send_output_file = notification.send_scan_output_file if notification else False
	msg = f'`vulnerability_scan` using Nuclei scanner started on {endpoints_count} endpoints'
	logger.warning(msg)
	if send_status:
		send_notification.delay(msg, scan_history_id, subscan_id)

	# Build templates
	# logger.info('Updating Nuclei templates ...')
	# run_command('nuclei -update-templates', shell=True, write_filepath=f'{results_dir}/commands.txt')

	templates = []
	if not (nuclei_templates or custom_nuclei_templates):
		logger.info(f'Using default nuclei templates {NUCLEI_DEFAULT_TEMPLATES_PATH}.')
		templates.append(NUCLEI_DEFAULT_TEMPLATES_PATH)

	if nuclei_templates:
		if ALL in nuclei_templates:
			template = NUCLEI_DEFAULT_TEMPLATES_PATH
			templates.append(template)
		else:
			templates.extend(nuclei_templates)
	
	if custom_nuclei_templates:
		custom_nuclei_template_paths = [f'{str(elem)}.yaml' for elem in custom_nuclei_templates]
		template = templates.extend(custom_nuclei_template_paths)

	# Build CMD
	cmd += ' -config /root/.config/nuclei/config.yaml' if use_nuclei_conf else ''
	# cmd += ' -debug' if DEBUG > 0 else ''
	cmd += f' -H "{custom_header}"' if custom_header else ''
	cmd += f' -l {input_path}'
	cmd += f' -c {str(concurrency)}' if concurrency > 0 else ''
	cmd += f' -proxy {proxy} ' if proxy else ''
	cmd += f' -retries {retries}' if retries > 0 else ''
	cmd += f' -rl {str(rate_limit)}' if rate_limit > 0 else ''
	cmd += f' -severity {severities_str}'
	cmd += f' -timeout {str(timeout)}' if timeout and timeout > 0 else ''
	for tpl in templates:
		cmd += f' -t {tpl}'

	# Run cmd
	results = []
	for line in stream_command(cmd, write_filepath=f'{results_dir}/commands.txt'):
		if not isinstance(line, dict):
			continue
		template = line['template']
		url = line['host']
		http_url = sanitize_url(line.get('matched-at'))
		subdomain_name = get_subdomain_from_url(url)
		subdomain = Subdomain.objects.get(
			name=subdomain_name,
			scan_history=scan,
			target_domain=domain)
		vuln_name = line['info'].get('name', '')
		vuln_type = line['type']
		vuln_severity = line['info'].get('severity', 'unknown')
		vuln_severity_id = NUCLEI_SEVERITY_MAP[vuln_severity]
		template_url = line['template-url']
		description = line['info'].get('description', '')

		# Get or create EndPoint object
		http_url = probe_url(http_url, first=True)
		if http_url:
			endpoint, created = save_endpoint(http_url, scan, domain, subdomain, results_dir, crawl=False)

		# Validate URL
		if not validators.url(http_url):
			logger.info(f'"{http_url}" is not a valid URL. Skipping')
			continue

		# Create vulnerability
		vulnerability = Vulnerability(
			name=vuln_name,
			type=vuln_type,
			subdomain=subdomain,
			endpoint=endpoint,
			scan_history=scan,
			target_domain=domain,
			http_url=http_url,
			severity=vuln_severity_id,
			template=template,
			template_url=template_url,
			template_id=line['template-id'],
			description=description,
			matcher_name=line.get('matcher-name', ''),
			curl_command=line.get('curl-command'),
			extracted_results=line.get('extracted-results', []),
			cvss_metrics=line['info'].get('classification', {}).get('cvss-metrics', ''),
			cvss_score=line['info'].get('classification', {}).get('cvss-score'),
			discovered_date=timezone.now(),
			open_status=True
		)
		logger.warning(f'Found {vuln_severity.upper()} vulnerability "{vuln_name}" of type {vuln_type} on {url} using template {template}')
		vulnerability.save()

		# Save vuln tags
		tags = line['info'].get('tags') or []
		for tag_name in tags:
			tag, created = VulnerabilityTags.objects.get_or_create(name=tag_name)
			if created:
				logger.warning(f'Found new vulnerability tag {tag_name}')
				vulnerability.tags.add(tag)
				vulnerability.save()

		# Save CVEs
		cve_ids = line['info'].get('classification', {}).get('cve-id') or []
		for cve_name in cve_ids:
			cve, created = CveId.objects.get_or_create(name=cve_name)
			if created:
				logger.warning(f'Found new CVE {cve_name}')
				vulnerability.cve_ids.add(cve)
				vulnerability.save()

		# Save CWEs
		cwe_ids = line['info'].get('classification', {}).get('cwe-id') or []
		for cwe_name in cwe_ids:
			cwe, created = CweId.objects.get_or_create(name=cwe_name)
			if created:
				logger.warning(f'Found new CWE {cwe_name}')
				vulnerability.cwe_ids.add(cwe)
				vulnerability.save()

		# Save vuln reference
		references = line['info'].get('reference') or []
		for ref_url in references:
			ref, created = VulnerabilityReference.objects.get_or_create(url=ref_url)
			if created:
				vulnerability.references.add(ref)
				vulnerability.save()

		# Save subscan id in vulnerability object
		if subscan:
			vulnerability.vuln_subscan_ids.add(subscan)
			vulnerability.save()
		
		# Save vulnerability object
		vulnerability.save()

		# Add to results
		results.append(line)

		# Send notification for all vulnerabilities except info
		url = vulnerability.http_url or vulnerability.subdomain
		if vuln_severity in ['low', 'medium', 'critical'] and send_vuln:
			url = urlparse(url)
			cve_str = ', '.join(f'`{cve_id}`' for cve_id in cve_ids)
			cwe_str = ', '.join(f'`{cwe_id}`' for cwe_id in cve_ids)
			tags_str = ', '.join(f'`{tag}`' for tag in tags)
			refs_str = '\n\t\t- '.join(f'`{ref}`' for ref in references)
			severity = vuln_severity.upper()
			message = f"""**{severity} vulnerability found on `{subdomain.name}`**
🡆 **URL:** [{url.path}{url.query}]({url.geturl()})
🡆 **Name:** {vuln_name}
🡆 **Type:** `{vuln_type}`
🡆 **Description:** {description}
🡆 **Template:** [{template}]({template_url})
🡆 **Tags:** {tags_str}"""
			if cve_str:
				message += f'\n\t🡆 **CVE:** {cve_str}'			
			if cwe_str:
				message += f'\n\t🡆 **CWE:** {cwe_str}'
			if refs_str:
				message += f'\n\t🡆 **References:** \n\t\t- {refs_str}\n\n'
			send_notification(message, scan_history_id, subscan_id)

		# Send report to hackerone
		hackerone_query = Hackerone.objects.all()
		if (hackerone_query.exists()
			and vuln_severity not in ('info', 'low')
			and vulnerability.target_domain.h1_team_handle):
			hackerone = hackerone_query.first()
			if hackerone.send_critical and vuln_severity == 'critical':
				send_hackerone_report(vulnerability.id)
			elif hackerone.send_high and vuln_severity == 'high':
				send_hackerone_report(vulnerability.id)
			elif hackerone.send_medium and vuln_severity == 'medium':
				send_hackerone_report(vulnerability.id)

	# Write results to JSON file
	with open(output_path, 'w') as f:
		json.dump(results, f, indent=4)

	# Send finish notif
	if send_status:
		vulns = Vulnerability.objects.filter(scan_history__id=scan.id)
		info_count = vulns.filter(severity=0).count()
		low_count = vulns.filter(severity=1).count()
		medium_count = vulns.filter(severity=2).count()
		high_count = vulns.filter(severity=3).count()
		critical_count = vulns.filter(severity=4).count()
		unknown_count = vulns.filter(severity=-1).count()
		vulnerability_count = info_count + low_count + medium_count + high_count + critical_count + unknown_count
		host = subdomain.name if subdomain_id else domain.name
		message = f"""`vulnerability_scan` has been completed for `{host}`: **{vulnerability_count} vulnerabilities discovered**.
🡆 **Critical:** {critical_count}
🡆 **High:** {high_count}
🡆 **Medium:** {medium_count}
🡆 **Low:** {low_count}
🡆 **Info:** {info_count}
🡆 **Unknown:** {unknown_count}"""
		send_notification(message, scan_history_id, subscan_id)
	if send_output_file:
		title = get_output_file_name(scan_history_id, subscan_id, filename)
		send_file_to_discord.delay(output_path, title)


#-------------------------#
# Untracked reNgine tasks #
#-------------------------#

@app.task
def http_crawl(
		scan_history_id,
		activity_id,
		engine_id=None,
		subdomain_id=None,
		yaml_configuration={},
		results_dir=None,
		description=None,
		urls=[],
		url_path='',
		method=None,
		subscan_id=None):
	"""Use httpx to query HTTP URLs for important info like page titles, http 
	status, etc...

	Args:
		scan_history (startScan.models.ScanHistory): ScanHistory instance.
		activity_id (int): Activity ID.
		yaml_configuration (dict): YAML configuration.
		results_dir (str): Results directory.
		description (str, optional): Task description shown in UI.
		urls (list, optional): A set of URLs to check. Overrides default 
			behavior which queries all endpoints related with this scan.
		url_path (str, optional): URL path to filter on.

	Returns:
		list: httpx results.
	"""
	timestamp = time.time()
	cmd = '/go/bin/httpx'
	custom_header = yaml_configuration.get(CUSTOM_HEADER)
	threads = yaml_configuration.get(THREADS, 0)
	results_dir = f'{results_dir}/httpx'
	os.makedirs(results_dir, exist_ok=True)
	output_file = f'{results_dir}/httpx_output_probe_{timestamp}.json'
	scan = ScanHistory.objects.get(pk=scan_history_id)
	subscan = SubScan.objects.get(pk=subscan_id) if subscan_id else None
	domain = scan.domain

	# Write httpx input file
	input_file = f'{results_dir}/httpx_input_probe_{timestamp}.txt'
	if urls: # direct passing URLs to check
		if url_path:
			urls = [u for u in urls if u.contains(url_path)]
		with open(input_file, 'w') as f:
			f.write('\n'.join(urls))
	else:
		get_http_urls(
			target_domain=domain,
			subdomain_id=subdomain_id,
			scan_history=scan,
			url_path=url_path,
			write_filepath=input_file)

	# Get random proxy
	proxy = get_random_proxy()

	# Run command
	cmd += f' -status-code -content-length -title -tech-detect -cdn -ip -follow-host-redirects -random-agent'
	cmd += f' -t {threads}' if threads > 0 else ''
	cmd += f' --http-proxy {proxy}' if proxy else ''
	cmd += f' -H "{custom_header}"' if custom_header else ''
	cmd += f' -json -l {input_file}'
	cmd += f' -x {method}' if method else ''
	results = []
	endpoint_ids = []
	for line in stream_command(cmd, echo=False, write_filepath=f'{results_dir}/commands.txt'):
		if not line or not isinstance(line, dict):
			continue
		try:
			content_length = line.get('content-length', 0)
			host = line.get('host', '')
			http_status = line.get('status-code', 0)
			input_url = line.get('input')
			http_url, is_redirect = extract_httpx_url(line)
			page_title = line.get('title', '')
			webserver = line.get('webserver')
			response_time = line.get('response-time')
			cdn = line.get('cdn', False)
			logger.info(f'{http_url} [{http_status}] [{content_length}] [{webserver}] [{response_time}] [{page_title}]')
			if response_time:
				response_time = float(''.join(ch for ch in line['response-time'] if not ch.isalpha()))
				if line['response-time'][-2:] == 'ms':
					response_time = response_time / 1000

			# Create Subdomain object in DB
			subdomain_name = get_subdomain_from_url(http_url)
			subdomain, _ = save_subdomain(subdomain_name, scan, domain)

			# Add HTTP URL + response info to subdomain if it is the subdomain's
			# root URL '/' or ''.
			url = urlparse(http_url)
			url_input = urlparse(input_url)
			url_input_path = url_input.path
			if not url_input.scheme:
				url_input_path = '/'.join(url_input_path.split('/')[1:])
			if url.netloc == subdomain_name and url_input_path in ['', '/']:
				subdomain.http_url = http_url
				subdomain.http_status = http_status
				subdomain.content_length = content_length
				subdomain.page_title = page_title
				subdomain.webserver = webserver
				subdomain.response_time = response_time
				subdomain.cname = ','.join(line.get('cnames', []))
				subdomain.save()
			
			# Save default HTTP URL to endpoint object in DB
			endpoint, created = save_endpoint(
				http_url,
				scan,
				domain,
				subdomain,
				results_dir,
				crawl=False,
				subscan=subscan)
			endpoint.is_default = True
			endpoint.http_status = http_status
			endpoint.page_title = page_title
			endpoint.content_length = content_length
			endpoint.webserver = webserver
			endpoint.response_time = response_time
			endpoint.save()
			if created and endpoint.is_alive:
				logger.warning(f'Found alive endpoint {endpoint.http_url} [{http_status}]')

			# Add endpoint to results
			line['final-url'] = http_url
			line['endpoint_id'] = endpoint.id
			line['is_redirect'] = is_redirect
			results.append(line)

			# Add technology objects to DB
			technologies = line.get('technologies', [])
			for technology in technologies:
				tech, _ = Technology.objects.get_or_create(name=technology)
				subdomain.technologies.add(tech)
				endpoint.technologies.add(tech)
				subdomain.save()
				endpoint.save()

			# Add IP objects for 'a' records to DB
			a_records = line.get('a', [])
			for ip_address in a_records:
				save_ip_address(ip_address, subdomain, subscan=subscan, cdn=cdn)

			# Add IP object for host in DB
			if host:
				save_ip_address(ip_address, subdomain, subscan=subscan, cdn=cdn)

			# Save subdomain and endpoint
			subdomain.save()
			endpoint.save()
			endpoint_ids.append(endpoint.id)

		except Exception as exception:
			logger.error(f'JSON line triggered an exception: {line}')
			logger.exception(exception)
			continue

	# Remove 'fake' alive endpoints that are just redirects to the same page
	remove_duplicate_endpoints(
		scan_history_id,
		domain.id,
		subdomain_id,
		filter_ids=endpoint_ids)

	# Write results to JSON file
	with open(output_file, 'w') as f:
		json.dump(results, f, indent=4)

	# Remove input file
	# run_command(f'rm {input_file} {output_file}', shell=True)

	return results


#---------------------#
# Notifications tasks #
#---------------------#

@app.task
def send_file_to_discord(file_path, title=None):
	send_file_to_discord_helper(file_path, title=title)


@app.task
def send_notification(
		message,
		scan_history_id=None,
		subscan_id=None,
		title=None,
		url=None,
		files=[],
		severity='info',
		fields={}):
	send_notification_helper(
		message,
		scan_history_id=scan_history_id,
		subscan_id=subscan_id,
		title=title,
		url=url,
		files=files,
		severity=severity,
		fields=fields)

#-------------#
# Utils tasks #
#-------------#

@app.task
def geo_localize(host, ip_id=None):
	"""Uses geoiplookup to find location associated with host.

	Args:
		host (str): Hostname.
		ip_id (int): IpAddress object id.

	Returns:
		startScan.models.CountryISO: CountryISO object from DB or None.
	"""
	if validators.ipv6(host):
		logger.info(f'Ipv6 "{host}" is not supported by geoiplookup. Skipping.')
		return None
	cmd = f'geoiplookup {host}'
	_, out, err = run_command(cmd)
	if 'IP Address not found' not in out and "can't resolve hostname" not in out:
		country_iso = out.split(':')[1].strip().split(',')[0]
		country_name = out.split(':')[1].strip().split(',')[1].strip()
		geo_object, _ = CountryISO.objects.get_or_create(
			iso=country_iso,
			name=country_name
		)
		if ip_id:
			ip = IpAddress.objects.get(pk=ip_id)
			ip.geo_iso = geo_object
			ip.save()
		return geo_object
	logger.info(f'Geo IP lookup failed for host "{host}"')
	return None


@app.task
def remove_duplicate_endpoints(scan_history_id, domain_id, subdomain_id=None, filter_ids=[], filter_status=[200, 301, 404]):
	"""Remove duplicate endpoints.

	Check for implicit redirections by comparing endpoints:
	- [x] `content_length` similarities indicating redirections
	- [x] `page_title` (check for same page title)
	- [ ] Sign-in / login page (check for endpoints with the same words)

	Args:
		scan_history_id: ScanHistory id.
		domain_id (int): Domain id.
		subdomain_id (int, optional): Subdomain id.
		filter_ids (list): List of endpoint ids to filter on.
		filter_status (list): List of HTTP status codes to filter on.
	"""
	endpoints = (
		EndPoint.objects
		.filter(scan_history__id=scan_history_id)
		.filter(target_domain__id=domain_id)
	)
	if filter_status:
		endpoints = endpoints.filter(http_status__in=filter_status)

	if subdomain_id:
		endpoints = endpoints.filter(subdomain__id=subdomain_id)

	if filter_ids:
		endpoints = endpoints.filter(id__in=filter_ids)

	for field_name in DEFAULT_ENDPOINT_DUPLICATE_FIELDS:
		cl_query = (
			endpoints
			.values_list(field_name)
			.annotate(mc=Count(field_name))
			.order_by('-mc')
		)
		for (field_value, count) in cl_query:
			if count > DELETE_DUPLICATES_THRESHOLD:
				eps_to_delete = (
					endpoints
					.filter(**{field_name: field_value})
					.order_by('discovered_date')
					.all()[1:]
				)
				msg = f'Deleting {len(eps_to_delete)} endpoints [reason: same {field_name} {field_value}]'
				for ep in eps_to_delete:
					url = urlparse(ep.http_url)
					if url.path in ['', '/', '/login']: # try do not delete the original page that other pages redirect to
						continue
					msg += f'\n\t {ep.http_url} [{ep.http_status}] [{field_name}={field_value}]'
					ep.delete()
				logger.warning(msg)


@app.task
def query_whois(ip_domain):
	"""Query WHOIS information for an IP or a domain name.
	
	Args:
		ip_domain (str): IP address or domain name.

	Returns:
		dict: WHOIS information.
	"""
	domain, _ = Domain.objects.get_or_create(name=ip_domain)
	if not domain.insert_date:
		domain.insert_date = timezone.now()
		domain.save()
	domain_info = domain.domain_info
	if not domain_info:
		logger.info(f'Domain info for "{domain}" not found in DB, querying whois')
		try:
			result = asyncwhois.whois_domain(ip_domain)
			whois = result.parser_output
			if not whois.get('domain_name'):
				raise Warning('No domain name in output')
		except Exception as e:
			return {
				'status': False,
				'ip_domain': ip_domain,
				'result': "unable to fetch records from WHOIS database.",
				'message': str(e)
			}
		created = whois.get('created')
		expires = whois.get('expires')
		updated = whois.get('updated')
		dnssec = whois.get('dnssec')

		# Save whois information in various tables
		domain_info = DomainInfo(
			raw_text=result.query_output.strip(),
			dnssec=dnssec,
			created=created,
			updated=updated,
			expires=expires)
		domain_info.save()
		
		# Record whois subfields in various DB models
		whois_fields = {
			'registrant':
				[
					('name', DomainRegisterName),
					('organization', DomainRegisterOrganization),
					('address', DomainAddress),
					('city', DomainCity),
					('state', DomainState),
					('zipcode', DomainZipCode),
					('country', DomainCountry),
					('phone', DomainPhone),
					('fax', DomainFax),
					('email', DomainEmail)
				],
			'admin': [
				('name', DomainRegisterName),
				('id', DomainRegistrarID),
				('organization', DomainRegisterOrganization),
				('address', DomainAddress),
				('city', DomainCity),
				('state', DomainState),
				('zipcode', DomainZipCode),
				('country', DomainCountry),
				('email', DomainEmail),
				('phone', DomainPhone),
				('fax', DomainFax)
			]
		}
		whois_fields['tech'] = whois_fields['admin'] # same fields
		logger.info(f'Gathering domain details for {ip_domain}...')
		for field_parent, fields in whois_fields.items():
			for (field_name, model_cls) in fields:
				field_fullname = f'{field_parent}_{field_name}' if field_parent != 'default' else field_name
				logger.info(f'Processing field {field_fullname}')
				field_content = whois.get(field_fullname)
				# serializer_cls = globals()[model_cls.__name__ + 'Serializer']

				# Skip empty fields
				if not field_content:
					continue

				# If field is an email, parse it with a regex
				if field_name == 'email':
					email_search = EMAIL_REGEX.search(str(field_content))
					field_content = email_search.group(0) if email_search else None

				# Create object in database
				try:
					obj, created = model_cls.objects.get_or_create(name=field_content)
				except Exception as e:
					logger.error(e)
					logger.error(f'Offending field: {field_parent}.{field_name}={field_content}')
					continue

				# Set attribute in domain_info
				setattr(domain_info, field_fullname, obj)
				domain_info.save()

			logger.warning(f'Saved DomainInfo for {ip_domain}.')

			# Whois status
			whois_status = whois.get('status', [])
			for _status in whois_status:
				domain_whois, _ = DomainWhoisStatus.objects.get_or_create(status=_status)
				domain_info.status.add(domain_whois)
				# domain_whois_json = DomainWhoisStatusSerializer(domain_whois, many=False).data

			# Nameservers
			nameservers = whois.get('name_servers', [])
			for name_server in nameservers:
				ns, _ = NameServers.objects.get_or_create(name=name_server)
				domain_info.name_servers.add(ns)

			# Save domain in DB
			domain.domain_info = domain_info
			domain.save()

	return {
		'status': True,
		'ip_domain': ip_domain,
		'domain': {
			'created': domain_info.created,
			'updated': domain_info.updated,
			'expires': domain_info.expires,
			'registrar': DomainRegistrarSerializer(domain_info.registrar).data['name'],
			'geolocation_iso': DomainCountrySerializer(domain_info.registrant_country).data['name'],
			'dnssec': domain_info.dnssec,
			'status': [status['status'] for status in DomainWhoisStatusSerializer(domain_info.status, many=True).data]
		},
		'registrant': {
			'name': DomainRegisterNameSerializer(domain_info.registrant_name).data['name'],
			'organization': DomainRegisterOrganizationSerializer(domain_info.registrant_organization).data['name'],
			'address': DomainAddressSerializer(domain_info.registrant_address).data['name'],
			'city': DomainCitySerializer(domain_info.registrant_city).data['name'],
			'state': DomainStateSerializer(domain_info.registrant_state).data['name'],
			'zipcode': DomainZipCodeSerializer(domain_info.registrant_zip_code).data['name'],
			'country': DomainCountrySerializer(domain_info.registrant_country).data['name'],
			'phone': DomainPhoneSerializer(domain_info.registrant_phone).data['name'],
			'fax': DomainFaxSerializer(domain_info.registrant_fax).data['name'],
			'email': DomainEmailSerializer(domain_info.registrant_email).data['name'],
		},
		'admin': {
			'name': DomainRegisterNameSerializer(domain_info.admin_name).data['name'],
			'id': DomainRegistrarIDSerializer(domain_info.admin_id).data['name'],
			'organization': DomainRegisterOrganizationSerializer(domain_info.admin_organization).data['name'],
			'address': DomainAddressSerializer(domain_info.admin_address).data['name'],
			'city': DomainCitySerializer(domain_info.admin_city).data['name'],
			'state': DomainStateSerializer(domain_info.admin_state).data['name'],
			'zipcode': DomainZipCodeSerializer(domain_info.admin_zip_code).data['name'],
			'country': DomainCountrySerializer(domain_info.admin_country).data['name'],
			'phone': DomainPhoneSerializer(domain_info.admin_phone).data['name'],
			'fax': DomainFaxSerializer(domain_info.admin_fax).data['name'],
			'email': DomainEmailSerializer(domain_info.admin_email).data['name'],
		},
		'technical_contact': {
			'name': DomainRegisterNameSerializer(domain_info.tech_name).data['name'],
			'id': DomainRegistrarIDSerializer(domain_info.tech_id).data['name'],
			'organization': DomainRegisterOrganizationSerializer(domain_info.tech_organization).data['name'],
			'address': DomainAddressSerializer(domain_info.tech_address).data['name'],
			'city': DomainCitySerializer(domain_info.tech_city).data['name'],
			'state': DomainStateSerializer(domain_info.tech_state).data['name'],
			'zipcode': DomainZipCodeSerializer(domain_info.tech_zip_code).data['name'],
			'country': DomainCountrySerializer(domain_info.tech_country).data['name'],
			'phone': DomainPhoneSerializer(domain_info.tech_phone).data['name'],
			'fax': DomainFaxSerializer(domain_info.tech_fax).data['name'],
			'email': DomainEmailSerializer(domain_info.tech_email).data['name'],
		},
		'nameservers': [ns['name'] for ns in NameServersSerializer(domain_info.name_servers, many=True).data],
		'raw_text': domain_info.raw_text
	}


@app.task
def remove_duplicate_endpoints(scan_history_id, domain_id, subdomain_id=None, filter_ids=[], filter_status=[200, 301, 404]):
	"""Remove duplicate endpoints.

	Check for implicit redirections by comparing endpoints:
	- [x] `content_length` similarities indicating redirections
	- [x] `page_title` (check for same page title)
	- [ ] Sign-in / login page (check for endpoints with the same words)

	Args:
		scan_history_id: ScanHistory id.
		domain_id (int): Domain id.
		subdomain_id (int, optional): Subdomain id.
		filter_ids (list): List of endpoint ids to filter on.
		filter_status (list): List of HTTP status codes to filter on.
	"""
	endpoints = (
		EndPoint.objects
		.filter(scan_history__id=scan_history_id)
		.filter(target_domain__id=domain_id)
	)
	if filter_status:
		endpoints = endpoints.filter(http_status__in=filter_status)

	if subdomain_id:
		endpoints = endpoints.filter(subdomain__id=subdomain_id)

	if filter_ids:
		endpoints = endpoints.filter(id__in=filter_ids)

	for field_name in DEFAULT_ENDPOINT_DUPLICATE_FIELDS:
		cl_query = (
			endpoints
			.values_list(field_name)
			.annotate(mc=Count(field_name))
			.order_by('-mc')
		)
		for (field_value, count) in cl_query:
			if count > DELETE_DUPLICATES_THRESHOLD:
				eps_to_delete = (
					endpoints
					.filter(**{field_name: field_value})
					.order_by('discovered_date')
					.all()[1:]
				)
				msg = f'Deleting {len(eps_to_delete)} endpoints [reason: same {field_name} {field_value}]'
				for ep in eps_to_delete:
					url = urlparse(ep.http_url)
					if url.path in ['', '/', '/login']: # try do not delete the original page that other pages redirect to
						continue
					msg += f'\n\t {ep.http_url} [{ep.http_status}] [{field_name}={field_value}]'
					ep.delete()
				logger.warning(msg)


@app.task
def run_command(cmd, echo=True, shell=False, write_filepath=None):
	"""Run a given command using subprocess module.

	Args:
		cmd (str): Command to run.
		shell (bool): Run within separate shell if True.
		write_filepath (bool): Write command to file.

	Returns:
		tuple: Tuple with return_code, stdout, stderr.
	"""
	logger.info(cmd)
	popen = subprocess.Popen(
		cmd if shell else cmd.split(),
		shell=shell,
		stdout=subprocess.PIPE,
		stderr=subprocess.PIPE,
		universal_newlines=True)
	out = ''
	for stdout_line in iter(popen.stdout.readline, ""):
		item = stdout_line.strip()
		out += '\n' + item
		if echo:
			logger.info(item)
	err = ''
	for stderr_line in iter(popen.stderr.readline, ""):
		item = stderr_line.strip()
		err += '\n' + item
		if echo:
			logger.info(item)
	return_code = popen.returncode
	if write_filepath:
		with open(write_filepath, 'a') as f:
			f.write(cmd + '\n')
	if echo:
		logger.info(out + err)
	return return_code, out, err


#-------------#
# Other utils #
#-------------#

def stream_command(cmd, echo=True, shell=False, write_filepath=None):
	"""Run a given command using subprocess module and stream its output live.

	Args:
		cmd (str): Command to run.
		shell (bool): Run within separate shell if True.
		write_filepath (bool): Write command to file.

	Yields:
		dict: stdout output converted to JSON.
		str: stdout output.
	"""
	logger.info(cmd)
	popen = subprocess.Popen(
		cmd if shell else cmd.split(),
		shell=shell,
		stdout=subprocess.PIPE,
		stderr=subprocess.PIPE,
		universal_newlines=True)
	for stdout_line in iter(popen.stdout.readline, ""):
		item = stdout_line.strip()
		if item.startswith(('{', '[')) and item.endswith(('}', ']')):
			try:
				item = json.loads(item)
				if echo:
					logger.info(item)
				yield item
				continue
			except Exception as e:
				pass
		if echo:
			logger.info(item)
		yield item
		popen.stdout.close()
	popen.wait()
	if write_filepath:
		with open(write_filepath, 'a') as f:
			f.write(cmd + '\n')


def extract_httpx_url(line):
	"""Extract final URL from httpx results. Always follow redirects to find
	the last URL.

	Args:
		line (dict): URL data output by httpx.

	Returns:
		tuple: (final_url, redirect_bool) tuple.
	"""
	status_code = line.get('status-code', 0)
	final_url = line.get('final-url')
	location = line.get('location')
	chain_status_codes = line.get('chain-status-codes', [])

	# Final URL is already looking nice, if it exists return it
	if final_url:
		return final_url, False
	http_url = line['url'] # fallback to url field

	# Handle redirects manually
	REDIRECT_STATUS_CODES = [301, 302]
	is_redirect = (
		status_code in REDIRECT_STATUS_CODES 
		or 
		any(x in REDIRECT_STATUS_CODES for x in chain_status_codes)
	)
	if is_redirect and location:
		if location.startswith('/'): # concatenate url netloc and path
			http_url = f'{http_url}{location}'
		else:
			http_url = location
	
	# Sanitize URL
	http_url = sanitize_url(http_url)

	return http_url, is_redirect


#-------------#
# OSInt utils #
#-------------#

def osint_discovery(scan_history, domain, yaml_configuration, results_dir, subscan=None):
	osint_config = yaml_configuration.get(OSINT) or {}
	osint_lookup = osint_config.get(OSINT_DISCOVER, OSINT_DEFAULT_LOOKUPS)
	osint_intensity = osint_config.get(INTENSITY, 'normal')
	documents_limit = osint_config.get(OSINT_DOCUMENTS_LIMIT, 50)
	data = {}
	meta_info = []
	emails = []
	creds = []

	# Get and save meta info
	if 'metainfo' in osint_lookup:
		if osint_intensity == 'normal':
			meta_dict = DottedDict({
				'osint_target': domain.name,
				'domain': domain,
				'scan_id': scan_history,
				'documents_limit': documents_limit
			})
			meta_info = get_and_save_meta_info(meta_dict)
		elif osint_intensity == 'deep':
			subdomains = Subdomain.objects.filter(scan_history=scan_history)
			for subdomain in subdomains:
				meta_dict = DottedDict({
					'osint_target': subdomain.name,
					'domain': domain,
					'scan_id': scan_history,
					'documents_limit': documents_limit
				})
				meta_info = get_and_save_meta_info(meta_dict)

	if 'emails' in osint_lookup:
		emails = get_and_save_emails(scan_history, results_dir)
		creds = get_and_save_leaked_credentials(scan_history, results_dir)

	if 'employees' in osint_lookup:
		data = get_and_save_employees(scan_history, domain, results_dir, subscan=subscan)
	
	data['emails'] = data.get('emails', []) + emails
	data['creds'] = creds
	data['meta_info'] = meta_info
	return data


def dorking(scan_history, yaml_configuration):
	# Some dork sources: https://github.com/six2dez/degoogle_hunter/blob/master/degoogle_hunter.sh
	config = yaml_configuration.get(OSINT) or {}
	dorks = config.get(OSINT_DORK, DORKS_DEFAULT_NAMES)
	results = []
	for dork in dorks:
		if dork == 'stackoverflow':
			dork_name = 'site:stackoverflow.com'
			dork_type = 'stackoverflow'
			results = get_and_save_dork_results(
				dork,
				dork_type,
				scan_history,
				in_target=False)

		elif dork == '3rdparty' :
			# look in 3rd party sitee
			dork_type = '3rdparty'
			lookup_websites = [
				'gitter.im',
				'papaly.com',
				'productforums.google.com',
				'coggle.it',
				'replt.it',
				'ycombinator.com',
				'libraries.io',
				'npm.runkit.com',
				'npmjs.com',
				'scribd.com',
				'gitter.im'
			]
			dork_name = ''
			for website in lookup_websites:
				dork_name = dork + ' | ' + 'site:' + website
				tmp_results = get_and_save_dork_results(
					dork_name[3:],
					dork_type,
					scan_history,
					in_target=False)
				results.extend(tmp_results)

		elif dork == 'social_media' :
			dork_type = 'Social Media'
			social_websites = [
				'tiktok.com',
				'facebook.com',
				'twitter.com',
				'youtube.com',
				'pinterest.com',
				'tumblr.com',
				'reddit.com'
			]
			dork_name = ''
			for website in social_websites:
				dork_name = dork + ' | ' + 'site:' + website
				tmp_results = get_and_save_dork_results(
					dork_name[3:],
					dork_type,
					scan_history,
					in_target=False)
				results.extend(tmp_results)

		elif dork == 'project_management' :
			dork_type = 'Project Management'
			project_websites = [
				'trello.com',
				'*.atlassian.net'
			]
			dork_name = ''
			for website in project_websites:
				dork_name = dork + ' | ' + 'site:' + website
				tmp_results = get_and_save_dork_results(
					dork_name[3:],
					dork_type,
					scan_history,
					in_target=False)
				results.extend(tmp_results)

		elif dork == 'code_sharing' :
			dork_type = 'Code Sharing Sites'
			code_websites = [
				'github.com',
				'gitlab.com',
				'bitbucket.org'
			]
			dork_name = ''
			for website in code_websites:
				dork_name = dork + ' | ' + 'site:' + website
				tmp_results = get_and_save_dork_results(
					dork_name[3:],
					dork_type,
					scan_history,
					in_target=False)
				results.extend(tmp_results)

		elif dork == 'config_files' :
			dork_type = 'Config Files'
			config_file_ext = [
				'env',
				'xml',
				'conf',
				'cnf',
				'inf',
				'rdp',
				'ora',
				'txt',
				'cfg',
				'ini'
			]

			dork_name = ''
			results = []
			for extension in config_file_ext:
				dork_name = dork + ' | ' + 'ext:' + extension
				tmp_results = get_and_save_dork_results(
					dork_name[3:],
					dork_type,
					scan_history,
					in_target=True)
				results.extend(tmp_results)

		if dork == 'jenkins' :
			dork_type = 'Jenkins'
			dork_name = 'intitle:\"Dashboard [Jenkins]\"'
			tmp_results = get_and_save_dork_results(
				dork_name,
				dork_type,
				scan_history,
				in_target=True)
			results.extend(tmp_results)

		elif dork == 'wordpress_files' :
			dork_type = 'Wordpress Files'
			inurl_lookup = [
				'wp-content',
				'wp-includes'
			]
			dork_name = ''
			for lookup in inurl_lookup:
				dork_name = dork + ' | ' + 'inurl:' + lookup
				tmp_results = get_and_save_dork_results(
					dork_name[3:],
					dork_type,
					scan_history,
					in_target=True)
				results.extend(tmp_results)

		elif dork == 'cloud_buckets':
			dork_type = 'Cloud Buckets'
			cloud_websites = [
				'.s3.amazonaws.com',
				'storage.googleapis.com',
				'amazonaws.com'
			]

			dork_name = ''
			for website in cloud_websites:
				dork_name = dork + ' | ' + 'site:' + website
				tmp_results = get_and_save_dork_results(
					dork_name[3:],
					dork_type,
					scan_history,
					in_target=False)
				results.extend(tmp_results)

		elif dork == 'php_error':
			dork_type = 'PHP Error'
			error_words = [
				'\"PHP Parse error\"',
				'\"PHP Warning\"',
				'\"PHP Error\"'
			]

			dork_name = ''
			for word in error_words:
				dork_name = dork + ' | ' + word
				tmp_results = get_and_save_dork_results(
					dork_name[3:],
					dork_type,
					scan_history,
					in_target=True)
				results.extend(tmp_results)

		elif dork == 'exposed_documents':
			dork_type = 'Exposed Documents'
			docs_file_ext = [
				'doc',
				'docx',
				'odt',
				'pdf',
				'rtf',
				'sxw',
				'psw',
				'ppt',
				'pptx',
				'pps',
				'csv'
			]

			dork_name = ''
			for extension in docs_file_ext:
				dork_name = dork + ' | ' + 'ext:' + extension
				tmp_results = get_and_save_dork_results(
					dork_name[3:],
					dork_type,
					scan_history,
					in_target=True)
				results.extend(tmp_results)

		elif dork == 'struts_rce':
			dork_type = 'Apache Struts RCE'
			struts_file_ext = [
				'action',
				'struts',
				'do'
			]

			dork_name = ''
			for extension in struts_file_ext:
				dork_name = dork + ' | ' + 'ext:' + extension
				tmp_results = get_and_save_dork_results(
					dork_name[3:],
					dork_type,
					scan_history,
					in_target=True)
				results.extend(tmp_results)

		elif dork == 'db_files':
			dork_type = 'Database Files'
			db_file_ext = [
				'sql',
				'db',
				'dbf',
				'mdb'
			]

			dork_name = ''
			for extension in db_file_ext:
				dork_name = dork_name + ' | ' + 'ext:' + extension
				tmp_results = get_and_save_dork_results(
					dork_name[3:],
					dork_type,
					scan_history,
					in_target=True)
				results.extend(tmp_results)

		elif dork == 'traefik':
			dork_name = 'intitle:traefik inurl:8080/dashboard'
			dork_type = 'Traefik'
			tmp_results = get_and_save_dork_results(
				dork_name,
				dork_type,
				scan_history,
				in_target=True)
			results.extend(tmp_results)

		elif dork == 'git_exposed':
			dork_name = 'inurl:\"/.git\"'
			dork_type = '.git Exposed'
			tmp_results = get_and_save_dork_results(
				dork_name,
				dork_type,
				scan_history,
				in_target=True)
			results.extend(tmp_results)
	return results


def get_and_save_dork_results(dork, type, scan_history, in_target=False):
	degoogle_obj = degoogle.dg()
	get_random_proxy()
	if in_target:
		query = f'{dork} site:{scan_history.domain.name}'
	else:
		query = f'{dork} \"{scan_history.domain.name}\"'
	degoogle_obj.query = query
	logger.info(f'Running degoogle with query "{query}" ...')
	results = degoogle_obj.run()
	logger.info(results)
	dorks = []
	for result in results:
		dork, created = Dork.objects.get_or_create(
			type=type,
			description=result['desc'],
			url=result['url']
		)
		if created:
			logger.warning(f'Found dork {dork}')
		scan_history.dorks.add(dork)
		dorks.append(dork)
	return results


def get_and_save_employees(scan_history, domain, results_dir, subscan=None):
	"""Get and save employees found with theHarvester.

	Args:
		scan_history (startScan.ScanHistory): Scan history object.
		domain (targetApp.Domain): Domain object.
		results_dir (str): Results directory.

	Returns:
		dict: Dict of emails, employees, hosts and ips found during crawling.
	"""
	theHarvester_dir = '/usr/src/github/theHarvester'
	output_filepath = f'{results_dir}/results.json'
	cmd  = f'cd {theHarvester_dir} && python3 theHarvester.py -d {domain.name} -b all -f {output_filepath}'

	# Update proxies.yaml
	proxy_query = Proxy.objects.all()
	if proxy_query.exists():
		proxy = proxy_query.first()
		if proxy.use_proxy:
			proxy_list = proxy.proxies.splitlines()
			yaml_data = {'http' : proxy_list}
			with open(f'{theHarvester_dir}/proxies.yaml', 'w') as file:
				yaml.dump(yaml_data, file)

	# Run cmd
	run_command(cmd, shell=True, write_filepath=f'{results_dir}/commands.txt')

	# Get file location
	if not os.path.isfile(output_filepath):
		logger.error(f'Could not open {output_filepath}')
		return

	# Load theHarvester results
	with open(output_filepath, 'r') as f:
		data = json.load(f)
	
	# Re-indent theHarvester JSON
	with open(output_filepath, 'w') as f:
		json.dump(data, f, indent=4)

	emails = data.get('emails', [])
	hosts = data.get('hosts', [])
	ips = data.get('ips', [])
	linkedin_people = data.get('linkedin_people', [])
	twitter_people = data.get('twitter_people', [])

	for email_address in emails:
		save_email(email_address, scan_history=scan_history)

	for people in linkedin_people:
		save_employee(people, designation='linkedin', scan_history=scan_history)

	for people in twitter_people:
		save_employee(people, designation='linkedin', scan_history=scan_history)

	for host in hosts:
		split = tuple(host.split(':'))
		http_url = split[0]
		subdomain_name = get_subdomain_from_url(http_url)
		subdomain, _ = save_subdomain(subdomain_name, scan_history, domain)
		save_endpoint(
			http_url,
			scan_history,
			domain,
			subdomain,
			results_dir,
			crawl=True,
			subscan=subscan)

	for ip_address in ips:
		save_ip_address(
			ip_address,
			subscan=subscan)
	return data


def get_and_save_emails(scan_history, results_dir):
	"""Get and save emails from Google, Bing and Baidu.

	Args:
		scan_history (startScan.ScanHistory): Scan history object.
		results_dir (str): Results directory.

	Returns:
		list: List of emails found.
	"""
	emails = []

	# Proxy settings
	get_random_proxy()

	# Gather emails from Google, Bing and Baidu
	try:
		logger.info('Getting emails from Google ...')
		email_from_google = get_emails_from_google(scan_history.domain.name)
		logger.info('Getting emails from Bing ...')
		email_from_bing = get_emails_from_bing(scan_history.domain.name)
		logger.info('Getting emails from Baidu ...')
		email_from_baidu = get_emails_from_baidu(scan_history.domain.name)
		emails = list(set(email_from_google + email_from_bing + email_from_baidu))
		logger.info(emails)
	except Exception as e:
		logger.exception(e)

	# Write to file
	leak_target_path = f'{results_dir}/emails.txt'
	with open(leak_target_path, 'w') as leak_target_file:
		for email_address in emails:
			save_email(email_address, scan_history)
			leak_target_file.write(f'{email_address}\n')

		# Fill leak_target_file with possible email address
		leak_target_file.write(f'%@{scan_history.domain.name}\n')
		leak_target_file.write(f'%@%.{scan_history.domain.name}\n')
		leak_target_file.write(f'%.%@{scan_history.domain.name}\n')
		leak_target_file.write(f'%.%@%.{scan_history.domain.name}\n')
		leak_target_file.write(f'%_%@{scan_history.domain.name}\n')
		leak_target_file.write(f'%_%@%.{scan_history.domain.name}\n')

	return emails


def get_and_save_leaked_credentials(scan_history, results_dir):
	"""Get and save leaked credentials to disk.

	Args:
		scan_history (startScan.ScanHistory): Scan history object.
		results_dir (str): Results directory.

	Returns:
		list[dict]: List of credentials info.
	"""
	logger.warning('Getting leaked credentials')
	leak_target_path = f'{results_dir}/emails.txt'
	leak_output_file = f'{results_dir}/h8mail_output.csv'
	cmd = f'h8mail -t {leak_target_path} -o {leak_output_file}'
	run_command(cmd, write_filepath=f'{results_dir}/commands.txt')
	with open(leak_output_file) as f:
		creds = [
			{k: v for k, v in row.items()}
			for row in csv.DictReader(f, skipinitialspace=True)
		]
		logger.info(f'h8mail output: {creds}')
	
	# TODO: go through h8mail output and save emails to DB
	creds_json = []
	# for cred in creds:
	# 	split = cred.split(':')
	# 	if len(split) == 2: # username:password
	# 		username, password = tuple(split)
	# 		creds_json.append({
	# 			'username': username,
	# 			'password': password
	# 		})
	# 		if cred['username'] == 'donate':
	# 			continue
	# 		if '@' in username: # email address found
	# 			logger.warning(f'Found email address with breached password')
	# 			email_obj, _ = Email.objects.get_or_create(address=username)
	# 			email_obj.password = password
	# 			email_obj.save()
	# 			scan_history.emails.add(email_obj)
	return creds_json


def get_and_save_meta_info(meta_dict):
	"""Extract metadata from Google Search.

	Args:
		meta_dict (dict): Info dict.

	Returns:
		list: List of startScan.MetaFinderDocument objects.
	"""
	logger.warning(f'Getting metadata for {meta_dict.osint_target}')

	# Proxy settings
	get_random_proxy()

	# Get metadata
	result = extract_metadata_from_google_search(meta_dict.osint_target, meta_dict.documents_limit)
	if not result:
		logger.error(f'No metadata result from Google Search for {meta_dict.osint_target}.')
		return

	# Add metadata info to DB
	results = []
	for metadata_name, metadata in result.get_metadata().items():
		subdomain = Subdomain.objects.get(
			scan_history=meta_dict.scan_id,
			name=meta_dict.osint_target)
		metadata = DottedDict(metadata)
		meta_finder_document = MetaFinderDocument(
			subdomain=subdomain,
			target_domain=meta_dict.domain,
			scan_history=meta_dict.scan_id,
			url=metadata.url,
			doc_name=metadata_name,
			http_status=metadata.status_code,
			producer=metadata.get('Producer', '').rstrip('\x00'),
			creator=metadata.get('Creator', '').rstrip('\x00'),
			creation_date=metadata.get('CreationDate', '').rstrip('\x00'),
			modified_date=metadata.get('ModDate', '').rstrip('\x00'),
			author=metadata.get('Author', '').rstrip('\x00'),
			title=metadata.get('Title', '').rstrip('\x00'),
			os=metadata.get('OSInfo', '').rstrip('\x00'))
		meta_finder_document.save()
		results.append(meta_finder_document)
	return results


#-----------------#
# Utils functions #
#-----------------#

def create_scan_activity(scan_history_id, message, status):
	scan_activity = ScanActivity()
	scan_activity.scan_of = ScanHistory.objects.get(pk=scan_history_id)
	scan_activity.title = message
	scan_activity.time = timezone.now()
	scan_activity.status = status
	scan_activity.save()
	return scan_activity.id


#--------------------#
# Database functions #
#--------------------#

def save_endpoint(
		http_url,
		scan_history,
		domain,
		subdomain,
		results_dir=None,
		crawl=False,
		subscan=None):
	"""Get or create EndPoint object. If crawl is True, also crawl the endpoint
	HTTP URL with httpx.

	Args:
		http_url (str): Input HTTP URL.
		scan_history (startScan.models.ScanHistory): ScanHistory object.
		domain (startScan.models.Domain): Domain object.
		subdomain (starScan.models.Subdomain): Subdomain object.
		results_dir (str, optional): Results directory.
		crawl (bool, optional): Run httpx on endpoint if True. Default: False.
		subscan (startScan.models.SubScan, optional): SubScan object.

	Returns:
		tuple: (startScan.models.EndPoint, created) where `created` is a boolean 
			indicating if the object is new or already existed.
	"""
	if crawl:
		results = http_crawl(
			scan_history.id,
			None,
			domain.id,
			subdomain.id,
			urls=[http_url],
			results_dir=results_dir)
		logger.info(results)
		if results:
			endpoint_id = results[0]['endpoint_id']
			endpoint = EndPoint.objects.get(pk=endpoint_id)
			return endpoint, False
		return None, False

	if not validators.url(http_url):
		logger.error(f'{http_url} is not a valid URL. Skipping.')
		return None, False

	http_url = sanitize_url(http_url)
	endpoint, created = EndPoint.objects.get_or_create(
		scan_history=scan_history,
		target_domain=domain,
		subdomain=subdomain,
		http_url=http_url)
	if created:
		endpoint.discovered_date = timezone.now()
		endpoint.save()
		if subscan:
			endpoint.endpoint_subscan_ids.add(subscan)
			endpoint.save()
	return endpoint, created


def save_subdomain(subdomain_name, scan_history, domain, subscan=None):
	"""Get or create Subdomain object.

	Args:
		subdomain_name (str): Subdomain name.
		scan_history (startScan.models.ScanHistory): ScanHistory object.
		domain (startScan.models.Domain): Domain object.

	Returns:
		tuple: (startScan.models.Subdomain, created) where `created` is a 
			boolean indicating if the object has been created in DB.
	"""
	if not (validators.domain(subdomain_name) or validators.ipv4(subdomain_name) or validators.ipv6(subdomain_name)):
		logger.error(f'{subdomain_name} is not a valid domain. Skipping.')
		return None, False
	subdomain, created = Subdomain.objects.get_or_create(
		scan_history=scan_history,
		target_domain=domain,
		name=subdomain_name)
	if created:
		logger.warning(f'Found new subdomain {subdomain_name}')
		subdomain.discovered_date = timezone.now()
		subdomain.save()
		if subscan:
			subdomain.subdomain_subscan_ids.add(subscan)
			subdomain.save()
	return subdomain, created


def save_email(email_address, scan_history=None):
	if not validators.email(email_address):
		logger.info(f'Email {email_address} is invalid. Skipping.')
		return None, False
	email, created = Email.objects.get_or_create(address=email_address)
	if created:
		logger.warning(f'Found new email address {email_address}')
	
	# Add email to ScanHistory
	if scan_history:
		scan_history.emails.add(email)
		scan_history.save()

	return email, created


def save_employee(name, designation, scan_history=None):
	employee, created = Employee.objects.get_or_create(
		name=name,
		designation=designation)
	if created:
		logger.warning(f'Found new employee {name}')
	
	# Add employee to ScanHistory
	if scan_history:
		scan_history.employees.add(employee)
		scan_history.save()

	return employee, created


def save_ip_address(ip_address, subdomain=None, subscan=None, **kwargs):
	if not (validators.ipv4(ip_address) or validators.ipv6(ip_address)):
		logger.info(f'IP {ip_address} is not a valid IP. Skipping.')
		return None, False
	ip, created = IpAddress.objects.get_or_create(address=ip_address)
	if created:
		logger.warning(f'Found new IP {ip_address}')

	# Set extra attributes
	for key, value in kwargs.items():
		setattr(ip, key, value)
	ip.save()

	# Add IP to subdomain
	if subdomain:
		subdomain.ip_addresses.add(ip)
		subdomain.save()

	# Add subscan to IP
	if subscan:
		ip.ip_subscan_ids.add(subscan)

	# Geo-localize IP asynchronously
	if created:
		geo_localize.delay(ip_address, ip.id)

	return ip, created

# TODO: replace all cmd += ' -{proxy}' if proxy else '' by this function
# def build_cmd(cmd, options, flags, sep=' '):
# 	for k, v in options.items():
# 		if v is None:
# 			continue
#		cmd += f' {k}{sep}{v}'
#	for flag in flags:
#		if not flag:
#			continue
#		cmd += f' --{flag}'
# 	return cmd
# build_cmd(cmd, proxy=proxy, option_prefix='-')


def process_imported_subdomains(
		imported_subdomains,
		scan_history,
		domain,
		results_dir):
	"""Take a list of subdomains imported and write them to from_imported.txt.

	Args:
		imported_subdomains (list): List of subdomains.
		scan_history (startScan.models.ScanHistory): ScanHistory instance.
		domain (startScan.models.Domain): Domain instance.
		results_dir (str): Results directory.
	"""
	# Validate imported subdomains
	subdomains = list(set([
		subdomain for subdomain in imported_subdomains 
		if validators.domain(subdomain) and domain.name == get_domain_from_subdomain(subdomain)
	]))
	if not subdomains:
		logger.info('No valid subdomains found in imported subdomains.')
		return

	with open(f'{results_dir}/from_imported.txt', 'w+') as output_file:
		for name in subdomains:
			subdomain_name = name.strip()
			subdomain, created = save_subdomain(subdomain_name, scan_history, domain)
			subdomain.is_imported_subdomain = True
			subdomain.save()
			output_file.write(f'{subdomain}\n')
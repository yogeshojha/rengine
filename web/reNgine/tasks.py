import csv
import json
from multiprocessing.sharedctypes import Value
import os
import pprint
import random
import subprocess
from datetime import datetime
from time import sleep

import asyncwhois
import validators
import whatportis
import yaml
from celery import chain, chord, group
from celery.result import allow_join_result
from celery.utils.log import get_task_logger
from degoogle import degoogle
from django.utils import timezone
from dotted_dict import DottedDict
from emailfinder.extractor import (get_emails_from_baidu, get_emails_from_bing,
                                   get_emails_from_google)
from metafinder.extractor import extract_metadata_from_google_search
from reNgine.celery import app
from reNgine.definitions import *
from reNgine.settings import DEBUG
from scanEngine.models import EngineType
from startScan.models import *
from startScan.models import EndPoint, Subdomain
from targetApp.models import Domain

from .common_func import *

"""
Celery tasks.
"""

logger = get_task_logger(__name__)


@app.task
def skip(*args, **kwargs):
	"""Task that does nothing to conditionally replace real tasks with."""
	pass


@app.task
def run_system_commands(cmd):
	"""Run a system command using os.system.

	Args:
		cmd (str): Command to run.
	"""
	logger.info(cmd)
	os.system(cmd)


@app.task
def initiate_subscan(
		scan_history_id,
		activity_id,
		subdomain_id,
		yaml_configuration,
		results_dir='/usr/src/scan_results',
		engine_id=None,
		scan_type=None):
	logger.info('Initiating Subtask')

	# Get scan history and yaml configuration for this subdomain
	subdomain = Subdomain.objects.get(pk=subdomain_id)
	scan_history = ScanHistory.objects.get(pk=subdomain.scan_history.id)

	# Create scan activity of SubScan Model
	subscan = SubScan(
		start_scan_date=timezone.now(),
		celery_id=initiate_subscan.request.id,
		scan_history=scan_history,
		subdomain=subdomain,
		type=scan_type,
		status=INITIATED_TASK
	)
	engine_id = engine_id or scan_history.scan_type.id
	engine = EngineType.objects.get(pk=engine_id)
	yaml_configuration = yaml.safe_load(engine.yaml_configuration)
	subscan.engine = engine
	subscan.save()

	results_dir = f'/usr/src/scan_results/{scan_history.results_dir}'
	timestr = datetime.strftime(timezone.now(), '%Y_%m_%d_%H_%M_%S')
	scan_name = f'{subdomain.name}_{timestr}'

	# Create results directory
	if not os.path.exists(results_dir):
		os.mkdir(results_dir)

	# Run task
	subscan.status = RUNNING_TASK
	subscan.save()
	method = globals().get(scan_type)
	if not method:
		logger.warning(f'Task {scan_type} is not supported by reNgine. Skipping')
		return
	filename = f'{scan_type}_{scan_name}.json'
	if scan_type in ['fetch_endpoints', 'vulnerability_scan']:
		filename = f'{scan_type}_{scan_name}.txt'
	scan_history.tasks.append(scan_type)
	scan_history.save()

	# Build header
	ctx = {
		'scan_history_id': scan_history.id,
		'activity_id': DYNAMIC_ID,
		'domain_id': subdomain.target_domain.id,
		'engine_id': engine_id,
		'subdomain_id': subdomain.id,
		'yaml_configuration': yaml_configuration,
		'results_dir': results_dir,
		'filename': filename
	}
	header = method.si(**ctx)

	# Build callback
	ctx = {
		'scan_history_id': scan_history.id,
		'activity_id': DYNAMIC_ID,
		'domain_id': subdomain.target_domain.id,
		'engine_id': engine_id,
		'subdomain_id': subdomain.id,
		'subscan_id': subscan.id,
		'description': 'Report subscan results'
	}
	callback = report.si(**ctx).set(link_error=[report.si(**ctx)])

	# Run Celery chord
	task = chord(header)(callback)

	return {
		'success': True,
		'task_id': task.id
	}


@app.task
def initiate_scan(
		scan_history_id,
		activity_id,
		domain_id,
		yaml_configuration,
		engine_id=None,
		results_dir='/usr/src/scan_results',
		scan_type=LIVE_SCAN,
		imported_subdomains=[],
		out_of_scope_subdomains=[],
		path=None):

	"""Initiate a new scan.

	Args:
		scan_history (startScan.models.ScanHistory): ScanHistory instance.
		activity_id (int): Activity ID.
		domain_id (int): Domain ID.
		yaml_configuration (dict): YAML configuration.
		results_dir (str): Results directory.
		engine_id (int): Engine ID.
		scan_type (int): Scan type (periodic, live).
		imported_subdomains (list): Imported subdomains.
		out_of_scope_subdomains (list): Out-of-scope subdomains.
		path (str): URL path.
	"""

	# Get ScanHistory
	scan_history = ScanHistory.objects.get(pk=scan_history_id)

	# Get engine
	engine_id = engine_id or scan_history.scan_type.id # scan history engine_id
	engine = EngineType.objects.get(pk=engine_id)

	# Get YAML config
	config = yaml.safe_load(engine.yaml_configuration)
	gf_patterns = config.get(GF_PATTERNS, [])

	# Get domain and set last_scan_date
	domain = Domain.objects.get(pk=domain_id)
	domain.last_scan_date = timezone.now()
	domain.save()

	# Create results directory
	timestr = datetime.strftime(timezone.now(), '%Y_%m_%d_%H_%M_%S')
	scan_dirname = f'{domain.name}_{timestr}'
	results_dir = f'{results_dir}/{scan_dirname}'
	os.makedirs(results_dir, exist_ok=True)

	# Get or create ScanHistory() object
	if scan_type == LIVE_SCAN: # immediate
		scan_history = ScanHistory.objects.get(pk=scan_history_id)
		scan_history.scan_status = RUNNING_TASK
	elif scan_type == SCHEDULED_SCAN: # scheduled
		scan_history = ScanHistory()
		scan_history.scan_status = INITIATED_TASK

	# Once the celery task starts, change the task status to started
	scan_history.scan_type = engine
	scan_history.celery_id = initiate_scan.request.id
	scan_history.domain = domain
	scan_history.start_scan_date = timezone.now()
	scan_history.tasks = engine.tasks
	scan_history.results_dir = scan_dirname
	add_gf_patterns = gf_patterns and 'fetch_url' in engine.tasks
	if add_gf_patterns:
		scan_history.used_gf_patterns = ','.join(gf_patterns)
	scan_history.save()

	# Put all imported subdomains into txt file and also in Subdomain model
	process_imported_subdomains(
		imported_subdomains,
		scan_history,
		domain,
		results_dir)

	# Create subdomain in DB
	Subdomain.objects.get_or_create(
		scan_history=scan_history,
		target_domain=domain,
		name=domain.name)

	# Initial URL discovery + checker on domain - will create at least 1 endpoint
	ctx = {
		'scan_history_id': scan_history.id,
		'activity_id': DYNAMIC_ID, # activity will be created dynamically
		'domain_id': domain.id,
		'results_dir': results_dir,
		'path': path
	}
	http_crawl(**ctx, description='Initial HTTP Crawl')
	fetch_url(**ctx, description='Initial URL Fetch')
	sleep(1)
	ctx['yaml_configuration'] = config # add config to ctx after above two tasks have run
	ctx['engine_id'] = engine_id

	# Send start notif
	notification = Notification.objects.first()
	send_status = notification.send_scan_status_notif if notification else False
	if send_status:
		count = len(engine.tasks)
		msg = f'*Scan started*\nRunning {count} tasks on "{domain.name}" with engine "{engine.engine_name}"'
		send_notification(msg)

	# Build Celery tasks, crafted according to the dependency graph below:
	# initiate_scan --> subdomain_discovery --> port_scan --> fetch_url --> http_crawl --> dir_file_fuzz
	#					osint 	   		              		  				 			   vulnerability_scan
	#		 		 						                  				 			   screenshot
	# 		   		 						           		   				 			   waf_detection
	skipped = skip.si(**ctx)
	header = group(
		# Subdomain tasks
		chain(
			subdomain_discovery.si(**ctx, description='Discover subdomains'),
			port_scan.si(**ctx, description='Scan ports'),
			fetch_url.si(**ctx, description='Fetch URLs'),
			http_crawl.si(**ctx, description='Crawl HTTP URLs'),
			group(
				dir_file_fuzz.si(**ctx, description='Fuzz directories & files'),
				waf_detection.si(**ctx, description='Detect WAFs'),
				vulnerability_scan.si(**ctx, description='Scan vulnerabilities'),
				screenshot.si(**ctx, description='Grab screenshots')
			)
		),
		# OSInt
		osint.si(**ctx, description='Perform OS Intelligence')
	).tasks

	# Build callback
	ctx = {
		'scan_history_id': scan_history.id,
		'activity_id': DYNAMIC_ID,
		'domain_id': domain.id,
		'engine_id': engine.id,
		'send_status': send_status,
		'description': 'Report results'
	}
	# callback = report.si(**ctx)
	callback = report.si(**ctx).set(link_error=[report.si(**ctx)])

	# Run Celery chord
	task = chord(header)(callback)

	return {
		'success': True,
		'task_id': task.id
	}


@app.task
def report(
		scan_history_id,
		activity_id,
		domain_id,
		engine_id=None,
		subdomain_id=None,
		send_status=False,
		subscan_id=None,
		description=None):
	"""Report task running after all other tasks.
	Mark ScanHistory object as completed and update with final status.
	Log run details and send notification.

	Args:
		scan_history (startScan.models.ScanHistory): ScanHistory instance.
		activity_id (int): Activity ID.
		domain_id (int): Domain ID.
		engine_id (int): Engine ID.
		subdomain_id (int): Subdomain ID.
		send_status (bool, optional): Send status notification. Default: False.
		description (str, optional): Task description.
	"""
	# Get domain, engine, scan_history objects
	domain = Domain.objects.get(pk=domain_id)
	engine = EngineType.objects.get(pk=engine_id)
	scan_history = ScanHistory.objects.get(pk=scan_history_id)

	# Get failed tasks and final status
	failed_tasks_count = (
		ScanActivity.objects
		.filter(scan_of=scan_history)
		.filter(status=FAILED_TASK)
		.count()
	)
	status = SUCCESS_TASK if failed_tasks_count == 0 else FAILED_TASK
	status_str = 'SUCCESS' if status else 'FAILED'

	# Update scan history
	scan_history.stop_scan_date = timezone.now()
	scan_history.scan_status = status
	scan_history.save()

	if subscan_id:
		subscan = SubScan.objects.get(pk=subscan_id)
		subscan.stop_scan_date = timezone.now()
		subscan.scan_status = status
		subscan.save()

	# Send notif
	host = domain.name
	if subdomain_id:
		subdomain = Subdomain.objects.get(pk=subdomain_id)
		host = subdomain.name
	msg = f'*Scan completed*\nFinished running tasks on "{host}" with engine {engine.engine_name}\nScan status:{status_str}'
	msg += f'\n{failed_tasks_count} tasks have a FAILED_TASK status.' if failed_tasks_count > 0 else ''
	logger.info(msg)

	# Send notif
	if send_status:
		send_notification(msg)


def process_imported_subdomains(
		imported_subdomains,
		scan_history,
		domain,
		results_dir):
	"""Take a list of subdomains imported and write them to from_imported.txt

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
			name = name.strip()
			subdomain, _ = Subdomain.objects.get_or_create(
				scan_history=scan_history,
				target_domain=domain,
				name=name)
			subdomain.is_imported_subdomain = True
			subdomain.save()
			output_file.write(f'{subdomain}\n')


@app.task
def subdomain_discovery(
		scan_history_id,
		activity_id,
		domain_id,
		engine_id=None,
		yaml_configuration={},
		results_dir=None,
		out_of_scope_subdomains=[],
		path=None,
		description=None):
	"""
	Uses a set of tools (see DEFAULT_SUBDOMAIN_SCAN_TOOLS) to scan all
	subdomains associated with a domain.

	Args:
		scan_history (startScan.models.ScanHistory): ScanHistory instance.
		activity_id (int): Activity ID.
		domain_id (int): Domain ID.
		yaml_configuration (dict): YAML configuration.
		results_dir (str): Results directory.
	"""
	# Config
	config = yaml_configuration.get(SUBDOMAIN_DISCOVERY, {})
	output_path = f'{results_dir}/subdomains.txt'
	threads = config.get(THREADS, 20)
	tools = config.get(USES_TOOLS, [])
	default_subdomain_tools = [tool.name.lower() for tool in InstalledExternalTool.objects.filter(is_default=True).filter(is_subdomain_gathering=True)]
	custom_subdomain_tools = [tool.name.lower() for tool in InstalledExternalTool.objects.filter(is_default=False).filter(is_subdomain_gathering=True)]
	send_status, send_scan_output, send_subdomain_changes, send_interesting = False, False, False, False
	notification = Notification.objects.first()
	if notification:
		send_status = notification.send_scan_status_notif
		send_scan_output = notification.send_scan_output_file
		send_subdomain_changes = notification.send_subdomain_changes_notif
		send_interesting = notification.send_interesting_notif

	scan_history = ScanHistory.objects.get(pk=scan_history_id)
	domain = Domain.objects.get(pk=domain_id)

	# Send start notif
	msg = f'Task "subdomain_discovery" has started for {domain.name}'
	logger.warning(msg)
	if send_status:
		send_notification(msg)

	# Write domain to file
	with open(f'{results_dir}/domain.txt', 'w') as f:
		f.write(domain.name + '\n')

	# Gather tools to run for subdomain scan
	if ALL in tools:
		tools = DEFAULT_SUBDOMAIN_SCAN_TOOLS + custom_subdomain_tools
	tools = [t.lower() for t in tools]

	# Run tools
	for tool in tools:
		try:
			if tool in default_subdomain_tools:
				if tool == 'amass-passive':
					cmd = f'amass enum -passive -d {domain.name} -o {results_dir}/from_amass.txt'
					cmd += ' -config /root/.config/amass.ini' if use_amass_config else ''
					logger.info(cmd)
					process = subprocess.Popen(cmd.split())
					process.wait()

				elif tool == 'amass-active':
					cmd = f'amass enum -active -d {domain.name} -o {results_dir}/from_amass_active.txt'
					use_amass_config = config.get(USE_AMASS_CONFIG, False)
					cmd += ' -config /root/.config/amass.ini' if use_amass_config else ''
					amass_wordlist_name = config.get(AMASS_WORDLIST, 'deepmagic.com-prefixes-top50000')
					wordlist_path = f'/usr/src/wordlist/{amass_wordlist_name}.txt'
					cmd += f' -brute -w {wordlist_path}'
					logger.info(cmd)
					process = subprocess.Popen(cmd.split())
					process.wait()

				elif tool == 'assetfinder':
					cmd = f'assetfinder --subs-only {domain.name} > {results_dir}/from_assetfinder.txt'
					logger.info(cmd)
					process = subprocess.Popen(cmd.split())
					process.wait()

				elif tool == 'sublist3r':
					cmd = f'python3 /usr/src/github/Sublist3r/sublist3r.py -d {domain.name} -t {threads} -o {results_dir}/from_sublister.txt'
					logger.info(cmd)
					process = subprocess.Popen(cmd.split())
					process.wait()

				elif tool == 'subfinder':
					cmd = f'subfinder -d {domain.name} -t {threads} -o {results_dir}/from_subfinder.txt'
					use_subfinder_config = config.get(USE_SUBFINDER_CONFIG, False)
					cmd += ' -config /root/.config/subfinder/config.yaml' if use_subfinder_config else ''
					logger.info(cmd)
					process = subprocess.Popen(cmd.split())
					process.wait()

				elif tool == 'oneforall':
					cmd = f'python3 /usr/src/github/OneForAll/oneforall.py --target {domain.name} run'
					logger.info(cmd)
					process = subprocess.Popen(cmd.split())
					process.wait()
					os.system(f'cut -d\',\' -f6 /usr/src/github/OneForAll/results/{domain.name}.csv >> {results_dir}/from_oneforall.txt')
					os.system(f'rm -rf /usr/src/github/OneForAll/results/{domain.name}.csv')

			elif tool in custom_subdomain_tools:
				tool_query = InstalledExternalTool.objects.filter(name__icontains=tool.lower())
				if tool_query.exists():
					custom_tool = tool_query.first()
					cmd = custom_tool.subdomain_gathering_command
					logger.info(cmd)
					if '{TARGET}' in cmd and '{OUTPUT}' in cmd:
						cmd = cmd.replace('{TARGET}', domain.name)
						cmd = cmd.replace('{OUTPUT}', f'{results_dir}/from_{tool}.txt')
						cmd = cmd.replace('{PATH}', custom_tool.github_clone_path) if '{PATH}' in cmd else cmd
						logger.info(f'Custom tool {tool} running with command {cmd}')
						process = subprocess.Popen(cmd.split())
						process.wait()
					else:
						logger.error(f'Missing {{TARGET}} and {{OUTPUT}} placeholders in {tool} configuration. Skipping.')

			else:
				logger.warning(
					f'Task "subdomain_discovery": "{tool}" is not supported by reNgine. Skipping.')
		except Exception as e:
			logger.error(
				f'Task "subdomain_discovery": "{tool}" raised an exception')
			logger.exception(e)

	# Gather all the tools' results in one single file. wrote subdomains into separate files,
	# cleanup tool results and sort all subdomains.
	os.system(f'cat {results_dir}/*.txt > {results_dir}/subdomain_collection.txt')
	os.system(f'sort -u {results_dir}/subdomain_collection.txt -o {results_dir}/subdomains.txt')
	# os.system(f'rm -f {results_dir}/from*')
	# os.system(f'rm -f {results_dir}/subdomain_collection.txt')

	# Parse the subdomain list file and store in db.
	with open(output_path) as f:
		lines = f.readlines()

	subdomain_count = 0
	for line in lines:
		subdomain_name = line.strip()
		valid_domain = validators.domain(subdomain_name)
		if not valid_domain:
			logger.error(f'Subdomain {subdomain_name} is not a valid domain name. Skipping.')
			continue
		if subdomain_name in out_of_scope_subdomains:
			logger.error(f'Subdomain {subdomain_name} is out of scope. Skipping.')
			continue
		subdomain, created = Subdomain.objects.get_or_create(
			scan_history=scan_history,
			target_domain=domain,
			name=subdomain_name)
		if created:
			logger.warning(f'Found new domain {subdomain_name}')
		subdomain_count += 1

	# Send notifications
	msg = f'Subdomain scan finished with {tools} for {domain.name} and *{subdomain_count}* subdomains were found'
	logger.warning(msg)
	if send_status:
		send_notification(msg)

	if send_scan_output:
		send_files_to_discord(f'{results_dir}/subdomains.txt')

	if send_subdomain_changes:
		added_subdomains = get_new_added_subdomain(scan_history.id, domain.id)
		removed_subdomains = get_removed_subdomain(scan_history.id, domain.id)

		if added_subdomains:
			message = f'**{added_subdomains.count()} new subdomains discovered on domain {domain.name}**'
			subdomains_str = '\n'.join([f'• {subdomain}' for subdomain in added_subdomains])
			message += subdomains_str
			send_notification(message)

		if removed_subdomains:
			message = f'**{removed_subdomains.count()} subdomains are no longer available on domain {domain.name}**'
			subdomains_str = '\n'.join([f'• {subdomain}' for subdomain in removed_subdomains])
			message += subdomains_str
			send_notification(message)

	if send_interesting:
		interesting_subdomains = get_interesting_subdomains(scan_history.id, domain.id)
		if interesting_subdomains:
			message = f'**{interesting_subdomains.count()} interesting subdomains found on domain {domain.name}**'
			subdomains_str = '\n'.join([f'• {subdomain}' for subdomain in removed_subdomains])
			message += subdomains_str
			send_notification(message)


def get_new_added_subdomain(scan_id, domain_id):
	"""Find domains added during the last run.

	Args:
		scan_id (int): startScan.models.ScanHistory ID.
		domain_id (int): startScan.models.Domain ID.

	Returns:
		django.models.querysets.QuerySet: query of newly added subdomains.
	"""
	scan_history = (
		ScanHistory.objects
		.filter(domain=domain_id)
		.filter(tasks__overlap=['subdomain_discovery'])
		.filter(id__lte=scan_id)
	)
	if not scan_history.count() > 1:
		return
	last_scan = scan_history.order_by('-start_scan_date')[1]
	scanned_host_q1 = (
		Subdomain.objects
		.filter(scan_history__id=scan_id)
		.values('name')
	)
	scanned_host_q2 = (
		Subdomain.objects
		.filter(scan_history__id=last_scan.id)
		.values('name')
	)
	added_subdomain = scanned_host_q1.difference(scanned_host_q2)
	return (
		Subdomain.objects
		.filter(scan_history=scan_id)
		.filter(name__in=added_subdomain)
	)


def get_removed_subdomain(scan_id, domain_id):
	scan_history = (
		ScanHistory.objects
		.filter(domain=domain_id)
		.filter(tasks__overlap=['subdomain_discovery'])
		.filter(id__lte=scan_id)
	)
	if not scan_history.count() > 1:
		return
	last_scan = scan_history.order_by('-start_scan_date')[1]
	scanned_host_q1 = (
		Subdomain.objects
		.filter(scan_history__id=scan_id)
		.values('name')
	)
	scanned_host_q2 = (
		Subdomain.objects
		.filter(scan_history__id=last_scan.id)
		.values('name')
	)
	removed_subdomains = scanned_host_q2.difference(scanned_host_q1)
	return (
		Subdomain.objects
		.filter(scan_history=last_scan)
		.filter(name__in=removed_subdomains)
	)


@app.task
def http_crawl(
		scan_history_id,
		activity_id,
		domain_id,
		engine_id=None,
		subdomain_id=None,
		yaml_configuration={},
		results_dir=None,
		description=None,
		path=None):
	"""Uses httpx to crawl domain for important info like page titles, http
	status, etc...

	Args:
		scan_history (startScan.models.ScanHistory): ScanHistory instance.
		activity_id (int): Activity ID.
		domain_id (int): Domain ID.
		yaml_configuration (dict): YAML configuration.
		results_dir (str): Results directory.
		description (str, optional): Task description shown in UI.
	"""
	cmd = '/go/bin/httpx'
	custom_header = yaml_configuration.get(CUSTOM_HEADER)
	threads = yaml_configuration.get(THREADS, 0)
	httpx_results_file = f'{results_dir}/httpx.json'
	domain = Domain.objects.get(pk=domain_id)
	scan_history = ScanHistory.objects.get(pk=scan_history_id)

	# Write httpx input file
	input_file = f'{results_dir}/subdomains.txt'
	urls = get_subdomains(
		domain,
		subdomain_id=subdomain_id,
		scan_history=scan_history,
		write_filepath=input_file,
		path=path)
	if not urls:
		logger.warning('Nofound. Skipping.')
		return

	# Get random proxy
	proxy = get_random_proxy()

	# Send notification
	notification = Notification.objects.first()
	send_status = notification.send_scan_status_notif if notification else False
	msg = f'Task "http_crawl" has started for {domain.name}'
	logger.warning(msg)
	if send_status:
		send_notification(msg)

	cmd += f' -status-code -content-length -title -tech-detect -cdn -ip -follow-host-redirects -random-agent -t {threads}'
	cmd += f' --http-proxy {proxy}' if proxy else ''
	cmd += f' -H "{custom_header}"' if custom_header else ''
	cmd += f' -json -l {input_file}'

	# Run command
	cmd = sanitize_cmd(cmd)
	logger.info(cmd)
	results = []
	for line in execute_live(cmd):
		if not isinstance(line, dict):
			continue
		try:
			results.append(line)
			# Locals
			content_length = line.get('content-length', 0)
			host = line.get('host', '')
			http_url = line.get('url')
			http_status = line.get('status-code', 0)
			page_title = line.get('title', '')
			webserver = line.get('webserver')
			response_time = line.get('response-time')
			if response_time:
				response_time = float(''.join(ch for ch in line['response-time'] if not ch.isalpha()))
				if line['response-time'][-2:] == 'ms':
					response_time = response_time / 1000

			# Save subdomain in DB
			if 'url' in line: # fallback for older versions of httpx
				name = line['input'].strip()
			else:
				name = http_url.split("//")[-1].strip()
			subdomain, _ = Subdomain.objects.get_or_create(
				target_domain=domain,
				scan_history=scan_history,
				name=name)
			discovered_date = timezone.now()
			subdomain.discovered_date = discovered_date
			subdomain.http_url = http_url
			subdomain.http_status = http_status
			subdomain.content_length = content_length
			subdomain.page_title = page_title
			subdomain.webserver = webserver
			subdomain.response_time = response_time
			subdomain.cname = ','.join(line.get('cnames', []))
			subdomain.save()

			# Save default HTTP URL to endpoint object in DB
			endpoint, _ = EndPoint.objects.get_or_create(
				scan_history=scan_history,
				target_domain=domain,
				subdomain=subdomain,
				http_url=http_url
			)
			endpoint.discovered_date = discovered_date
			endpoint.is_default=True
			endpoint.http_status=http_status
			endpoint.page_title=page_title
			endpoint.content_length=content_length
			endpoint.webserver=webserver
			endpoint.response_time=response_time
			if endpoint.is_alive():
				logger.warning(f'Found alive endpoint at {endpoint} with status {http_status}')

			# Add technology objects to DB
			technologies = line.get('technologies', [])
			for technology in technologies:
				tech, _ = Technology.objects.get_or_create(name=technology)
				subdomain.technologies.add(tech)
				endpoint.technologies.add(tech)
				subdomain.save()
				endpoint.save()

			# Add ip objects to DB
			a_records = line.get('a', [])
			for ip_address in a_records:
				ip, _ = IpAddress.objects.get_or_create(address=ip_address)
				ip.is_cdn = line.get('cdn', False)
				ip.save()

				# Add CountryISO to DB
				geo_object = geo_localize(ip_address)
				if geo_object:
					ip.geo_iso = geo_object
					ip.save()

				# Add IP address to subdomain
				subdomain.ip_addresses.add(ip)
				subdomain.save()

			# Add IP object in DB
			if host:
				ip, _ = IpAddress.objects.get_or_create(address=host)
				ip.is_cdn = line.get('cdn', False)
				ip.save()

				# Add geo iso
				geo_object = geo_localize(host)
				if geo_object:
					ip.geo_iso = geo_object
					ip.save()

				# Add IP address to subdomain
				subdomain.ip_addresses.add(ip)
				subdomain.save()

			# Save subdomain and endpoint
			subdomain.save()
			endpoint.save()

		except Exception as exception:
			logger.error(f'JSON line triggered an exception: {line}')
			logger.exception(exception)
			continue

	# Write results to JSON file
	with open(httpx_results_file, 'w') as f:
		json.dump(results, f, indent=4)

	# Send finish notification
	alive_count = (
		Subdomain.objects
		.filter(scan_history__id=scan_history.id)
		.values('name')
		.distinct()
		.filter(http_status__exact=200)
		.count()
	)
	msg = f'Task "http_crawl" has finished gathering endpoints for {domain.name} and has discovered {alive_count} "alive" endpoint'
	logger.warning(msg)
	if send_status:
		send_notification(msg)


def geo_localize(host):
	"""Uses geoiplookup to find location associated with host.

	Args:
		host (str): Hostname.

	Returns:
		startScan.models.CountryISO: CountryISO object from DB or None.
	"""
	cmd = f'geoiplookup {host}'
	out = subprocess.getoutput([cmd])
	if 'IP Address not found' not in out and "can't resolve hostname" not in out:
		country_iso = out.split(':')[1].strip().split(',')[0]
		country_name = out.split(':')[1].strip().split(',')[1].strip()
		geo_object, _ = CountryISO.objects.get_or_create(
			iso=country_iso,
			name=country_name
		)
		return geo_object
	logger.info(f'Geo IP lookup failed for host "{host}"')
	return None


@app.task
def screenshot(
		scan_history_id,
		activity_id,
		domain_id,
		engine_id=None,
		subdomain_id=None,
		yaml_configuration={},
		results_dir=None,
		path=None,
		description=None):
	"""Uses EyeWitness to gather screenshot of a domain and/or url.

	Args:
		scan_history (startScan.models.ScanHistory): ScanHistory instance.
		activity_id (int): Activity ID.
		domain_id (int): Domain ID.
		yaml_configuration (dict): YAML configuration.
		results_dir (str): Results directory.
		path (str): URL path.
		description (str, optional): Task description shown in UI.
	"""

	# Config
	screenshots_path = f'{results_dir}/screenshots'
	result_csv_path = f'{results_dir}/screenshots/Requests.csv'
	alive_endpoints_file = f'{results_dir}/endpoints_alive.txt'
	config = yaml_configuration.get(SCREENSHOT, {})
	timeout = config.get(TIMEOUT, 0)
	threads = config.get(THREADS, 0)
	scan_history = ScanHistory.objects.get(pk=scan_history_id)
	domain = Domain.objects.get(pk=domain_id)

	# Get alive endpoints to screenshot
	get_endpoints(
		domain,
		subdomain_id=subdomain_id,
		scan_history=scan_history,
		is_alive=True,
		path=path,
		write_filepath=alive_endpoints_file)

	# Build cmd
	cmd = f'python3 /usr/src/github/EyeWitness/Python/EyeWitness.py -f {alive_endpoints_file} -d {screenshots_path} --no-prompt'
	cmd += f' --timeout {timeout}' if timeout > 0 else ''
	cmd += f' --threads {threads}' if threads > 0 else ''

	# Send start notif
	notification = Notification.objects.first()
	send_status = notification.send_scan_status_notif if notification else False
	msg = f'Task "screenshot" has started for {domain.name}'
	logger.warning(msg)
	if send_status:
		send_notification(msg)

	# Run cmd
	logger.info(cmd)
	process = subprocess.Popen(cmd.split())
	process.wait()
	if not os.path.isfile(result_csv_path):
		logger.error(f'Could not load EyeWitness results at {result_csv_path} for {domain.name}.')
		return

	# Loop through results and save objects in DB
	with open(result_csv_path, 'r') as file:
		reader = csv.reader(file)
		for row in reader:
			"Protocol,Port,Domain,Request Status,Screenshot Path, Source Path"
			protocol, port, subdomain_name, status, screenshot_path, source_path = tuple(row)
			logger.info(f'{protocol}:{port}:{subdomain_name}:{status}')
			subdomain_query = (
				Subdomain.objects
				.filter(scan_history__id=scan_history.id, name=subdomain_name)
			)
			if status == 'Successful' and subdomain_query.exists():
				subdomain = subdomain_query.first()
				subdomain.screenshot_path = screenshot_path.replace('/usr/src/scan_results/', '')
				subdomain.save()
				logger.warning(f'Added screenshot for {subdomain.name} to DB')

	# Remove all db, html extra files in screenshot results
	os.system('rm -rf {0}/*.csv {0}/*.db {0}/*.js {0}/*.html {0}/*.css'.format(screenshots_path))
	os.system(f'rm -rf {screenshots_path}/source')

	# Send finish notif
	if send_status:
		send_notification(f'Task "screenshot" has finished successfully.')


@app.task
def port_scan(
		scan_history_id,
		activity_id,
		domain_id,
		engine_id=None,
		yaml_configuration={},
		results_dir=None,
		subdomain_id=None,
		path=None,
		filename='ports.json',
		description=None
	):
	"""Run port scan.

	Args:
		scan_history (startScan.models.ScanHistory): ScanHistory instance.
		activity_id (int): Activity ID.
		domain_id (int): Domain ID.
		yaml_configuration (dict): YAML configuration.
		results_dir (str): Results directory.
		path (str): URL path.
		description (str, optional): Task description shown in UI.

	Returns:
		list: List of open ports (dict).
	"""
	cmd = 'naabu -json -exclude-cdn'
	config = yaml_configuration.get(PORT_SCAN, {})
	exclude_subdomains = config.get('exclude_subdomains', False)
	exclude_ports = config.get(EXCLUDE_PORTS, [])
	ports = config.get(PORTS, NAABU_DEFAULT_PORTS)
	naabu_rate = config.get(NAABU_RATE, 0)
	use_naabu_config = config.get(USE_NAABU_CONFIG, False)
	exclude_ports_str = ','.join(exclude_ports)
	output_file = f'{results_dir}/{filename}'
	domain = Domain.objects.get(pk=domain_id)
	scan_history = ScanHistory.objects.get(pk=scan_history_id)

	# Random sleep to prevent ip and port being overwritten
	sleep(random.randint(1,5))

	# Get subdomains
	hosts = get_subdomains(
		domain,
		subdomain_id=subdomain_id,
		scan_history=scan_history,
		path=path,
		exclude_subdomains=exclude_subdomains)
	hosts_str = ','.join(hosts)
	cmd += f' -host {hosts_str}'

	# Send start notif
	notification = Notification.objects.first()
	send_status = notification.send_scan_status_notif if notification else False
	send_output_file = notification.send_scan_output_file if notification else False
	msg = f'Task "port_scan" has started for {hosts}'
	logger.warning(msg)
	if send_status:
		send_notification(msg)

	# Get ports
	if 'full' in ports:
		ports_str = ' -p "-"'
	elif 'top-100' in ports:
		ports_str = ' -top-ports 100'
	elif 'top-1000' in ports:
		ports_str = ' -top-ports 1000'
	else:
		ports_str = ','.join(ports)
		ports_str = f' -p {ports_str}'

	proxy = get_random_proxy()
	cmd += f' -proxy "{proxy}"'
	cmd += ' -config /root/.config/naabu/config.yaml' if use_naabu_config else ''
	cmd += f' -rate {naabu_rate}' if naabu_rate > 0 else ''
	cmd += ports_str
	cmd += f' -exclude-ports {exclude_ports_str}' if exclude_ports else ''

	# Writing port results
	ports = []
	logger.info(cmd)
	for line in execute_live(cmd):
		# TODO: Update Celery task status continously
		if not isinstance(line, dict):
			continue
		port_number = line['port']
		ip_address = line['ip']
		host = line.get('host') or ip_address
		if port_number == 0:
			continue
		logger.warning(f'Found open port {port_number} on {ip_address} ({host})')
		ports.append(line)

		# Add port to DB
		port, _ = Port.objects.get_or_create(number=port_number)
		port.is_uncommon = port_number in UNCOMMON_WEB_PORTS
		port_details = whatportis.get_ports(str(port_number))
		if len(port_details) > 0:
			port.service_name = port_details[0].name
			port.description = port_details[0].description
		port.save()

		# Add IP DB
		ip, _ = IpAddress.objects.get_or_create(address=ip_address)
		ip.ports.add(port)
		ip.save()
		# if subscan:
		# 	ip.ip_subscan_ids.add(subscan)
		# 	ip.save()

		# Add IP to Subdomain in DB
		subdomain = Subdomain.objects.filter(
			target_domain=domain,
			name=host,
			scan_history=scan_history
		).first()
		subdomain.ip_addresses.add(ip)
		subdomain.save()

		# Add endpoint
		protocol = 'https' if port_number == 443 else 'http'
		http_url = f'{protocol}://{host}:{port_number}'
		EndPoint.objects.get_or_create(
			scan_history=scan_history,
			target_domain=domain,
			subdomain=subdomain,
			http_url=http_url
		)


	# Send end notif and output file
	msg = f'Task "port_scan" has finished for {domain.name} and has identified {len(ports)} ports'
	logger.warning(msg)
	if send_status:
		send_notification(msg)
	if send_output_file:
		with open(output_file, 'w') as f:
			json.dump(ports, f, indent=4)
		send_files_to_discord(output_file)

	return ports


@app.task
def waf_detection(
		scan_history_id,
		activity_id,
		domain_id,
		engine_id=None,
		subdomain_id=None,
		yaml_configuration={},
		results_dir=None,
		path=None,
		description=None):
	"""
	Uses wafw00f to check for the presence of a WAF.

	Args:
		scan_history (startScan.models.ScanHistory): ScanHistory instance.
		activity_id (int): Activity ID.
		domain_id (int): Domain ID.
		yaml_configuration (dict): YAML configuration.
		results_dir (str): Results directory.
		path (str): URL path.
		description (str, optional): Task description shown in UI.

	Returns:
		list: List of startScan.models.Waf objects.
	"""
	domain = Domain.objects.get(pk=domain_id)
	scan_history = ScanHistory.objects.get(pk=scan_history_id)

	# Send start notif
	notification = Notification.objects.first()
	send_status = notification.send_scan_status_notif if notification else False
	msg = f'Task "waf_detection" has started for {domain.name}'
	logger.warning(msg)
	if send_status:
		send_notification(msg)

	# Get alive endpoints from DB
	input_path = f'{results_dir}/endpoints_alive.txt'
	output_path = f'{results_dir}/wafw00f.txt'
	get_endpoints(
		domain,
		subdomain_id=subdomain_id,
		scan_history=scan_history,
		is_alive=True,
		path=path,
		write_filepath=input_path)

	cmd = f'wafw00f -i {input_path} -o {output_path}'
	logger.info(cmd)
	process = subprocess.Popen(cmd.split())
	process.wait()

	if not os.path.isfile(output_path):
		logger.error(f'Could not find {output_path}')
		return

	with open(output_path) as file:
		lines = file.readlines()

	wafs = []
	for line in lines:
		# split by 3 space!
		splitted = line.split('   ')
		# remove all empty strings
		strs = [string for string in splitted if string]
		# 0th pos is url and 1st pos is waf, remove /n from waf
		waf = strs[1].strip()
		waf_name = waf[:waf.find('(')].strip()
		waf_manufacturer = waf[waf.find('(')+1:waf.find(')')].strip()
		http_url = strs[0].strip()
		if not waf_name or waf_name == 'None':
			continue

		# Add waf to db
		waf_obj, _ = Waf.objects.get_or_create(
			name=waf_name,
			manufacturer=waf_manufacturer
		)
		waf_obj.save()
		wafs.append(waf_obj)

		# Add waf info to Subdomain in DB
		subdomain_query = Subdomain.objects.filter(scan_history=scan_history, http_url=http_url)
		if subdomain_query.exists():
			subdomain = subdomain_query.first()
			subdomain.waf.add(waf_obj)
		subdomain.save()

	# Send end notif
	msg = f'Task "waf_detection" has finished for {domain.name}'
	logger.info(msg)
	if send_status:
		send_notification(msg)

@app.task
def dir_file_fuzz(
		scan_history_id,
		activity_id,
		domain_id,
		engine_id=None,
		subdomain_id=None,
		yaml_configuration={},
		results_dir=None,
		path=None,
		filename='dirs.json',
		description=None):
	"""Perform directory scan, and currently uses `ffuf` as a default tool.

	Args:
		scan_history (startScan.models.ScanHistory): ScanHistory instance.
		activity_id (int): Activity ID.
		domain_id (int): Domain ID.
		yaml_configuration (dict): YAML configuration.
		results_dir (str): Results directory.
		description (str, optional): Task description shown in UI.
	"""
	scan_history = ScanHistory.objects.get(pk=scan_history_id)
	domain = Domain.objects.get(pk=domain_id)
	if subdomain_id:
		subdomain = Subdomain.objects.get(pk=subdomain_id)
		host = subdomain.name
	else:
		host = domain.name

	# Config
	cmd = 'ffuf'
	output_path = f'{results_dir}/{filename.strip()}'
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
	recursive_level = config.get(RECURSIVE_LEVEL)
	stop_on_error = config.get(STOP_ON_ERROR, False)
	timeout = config.get(TIMEOUT, 0)
	threads = config.get(THREADS, 0)
	use_extensions = config.get(USE_EXTENSIONS)
	wordlist_name = config.get(WORDLIST, 'dicc')

	# Send start notification
	notification = Notification.objects.first()
	send_status = notification.send_scan_status_notif if notification else False
	msg = f'Task "dir_file_fuzz" has started for {host}'
	logger.warning(msg)
	if send_status:
		send_notification(msg)

	# Get wordlist
	wordlist_name = 'dicc' if wordlist_name == 'default' else wordlist_name
	wordlist_path = f'/usr/src/wordlist/{wordlist_name}.txt'

	# Build command
	cmd += f' -w {wordlist_path}'
	cmd += f' -e {extensions_str}' if extensions and use_extensions else ''
	cmd += f' -maxtime {max_time}' if max_time > 0 else ''
	cmd += f' -p "{delay}"' if delay > 0 else ''
	cmd += f' -recursion -recursion-depth {recursive_level} ' if recursive_level else ''
	cmd += f' -t {threads}' if threads > 0 else ''
	cmd += f' -timeout {timeout}' if timeout > 0 else ''
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
			.filter(scan_history__id=scan_history.id, http_url__isnull=False)
		)

	# Loop through subdomains and run command
	for subdomain in subdomains_fuzz:
		final_cmd = cmd

		# Delete any existing dirs.json
		if os.path.isfile(output_path):
			os.system(f'rm -rf {output_path}')

		# HTTP URL
		http_url = subdomain.http_url or subdomain.name
		http_url = http_url.strip()
		if path:
			http_url += '/path'
		if not http_url.endswith('/FUZZ'):
			http_url += '/FUZZ'
		if not http_url.startswith('http'):
			http_url = f'https://{http_url}'
		logger.info(f'Running ffuf on {http_url} ...')

		# Proxy
		proxy = get_random_proxy()
		if proxy:
			final_cmd += f' -x "{proxy}"'

		final_cmd += f' -u {http_url} -o {output_path} -of json'

		# Run cmd
		logger.info(final_cmd)
		process = subprocess.Popen(final_cmd.split())
		process.wait()

		if not os.path.isfile(output_path):
			logger.error(f'Could not read output file "{output_path}"')
			return

		with open(output_path, "r") as f:
			data = json.load(f)

		if not data:
			logger.error(f'No input data was found in {output_path}')
			return

		# Initialize DirectoryScan object
		subdomain = Subdomain.objects.get(pk=subdomain.id)
		directory_scan = DirectoryScan()
		directory_scan.scanned_date = timezone.now()
		directory_scan.command_line = data['commandline']
		directory_scan.save()
		# TODO: URL Models to be created here

		for result in data['results']:
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
			dfile_query = DirectoryFile.objects.filter(
				name=name,
				length__exact=length,
				http_status__exact=status,
				words__exact=words,
				url=url,
				content_type=content_type
			)
			if dfile_query.exists():
				file = dfile_query.first()
			else:
				file = DirectoryFile(
					name=name,
					length=length,
					lines=lines,
					http_status=status,
					words=words,
					url=url,
					content_type=content_type)
				file.save()
			directory_scan.directory_files.add(file)

		# if subscan:
		# 	directory_scan.dir_subscan_ids.add(subscan)

		directory_scan.save()
		subdomain.directories.add(directory_scan)
		subdomain.save()

	msg = f'ffuf directory bruteforce has finished for {host}'
	if send_status:
		send_notification(msg)


@app.task
def fetch_url(
		scan_history_id,
		activity_id,
		domain_id,
		engine_id=None,
		subdomain_id=None,
		yaml_configuration={},
		results_dir=None,
		filename='urls.txt',
		path=None,
		description=None):
	"""Fetch URLs using different tools like gauplus, gospider, waybackurls ...

	Args:
		scan_history (startScan.models.ScanHistory): ScanHistory instance.
		activity_id (int): Activity ID.
		domain_id (int): Domain ID.
		subdomain_id (int): Subdomain ID.
		yaml_configuration (dict): YAML configuration.
		results_dir (str): Results directory.
		filename (str): Filename.
		path (str): URL path.
		description (str, optional): Task description shown in UI.
	"""
	scan_history = ScanHistory.objects.get(pk=scan_history_id)
	domain = Domain.objects.get(pk=domain_id)

	# Config
	config = yaml_configuration.get(FETCH_URL, {})
	gf_patterns = config.get(GF_PATTERNS, [])
	ignore_file_extension = config.get(IGNORE_FILE_EXTENSION, [])
	scan_intensity = config.get(INTENSITY, DEFAULT_ENDPOINT_SCAN_INTENSITY)
	tools = config.get(USES_TOOLS, DEFAULT_ENDPOINT_SCAN_TOOLS)
	custom_header = yaml_configuration.get(CUSTOM_HEADER)
	proxy = get_random_proxy()
	input_path = f'{results_dir}/subdomains.txt'
	output_path = f'{results_dir}/{filename}'
	exclude_subdomains = config.get('exclude_subdomains', False)

	# Get URLs to scan
	urls = get_subdomains(
		domain,
		subdomain_id=subdomain_id,
		scan_history=scan_history,
		write_filepath=input_path,
		path=path,
		exclude_subdomains=exclude_subdomains)
	if not urls:
		logger.warning('No URLs found. Skipping.')
		return

	# Combine old gf patterns with new ones
	if gf_patterns:
		scan_history.used_gf_patterns = ','.join(gf_patterns)
		scan_history.save()

	# Start notif
	notification = Notification.objects.first()
	send_status = notification.send_scan_status_notif if notification else False
	send_output_file = notification.send_scan_output_file if notification else False
	msg = f'Task "fetch_url" started for {domain.name}'
	logger.warning(msg)
	if send_status:
		send_notification(msg)

	# Domain regex
	domain_regex = f"\'https?://([a-z0-9]+[.])*{domain.name}.*\'"

	# Tools cmds
	gauplus_cmd = f'cat {input_path} | gauplus --random-agent | grep -Eo {domain_regex} > {results_dir}/urls_gau.txt'
	hakrawler_cmd = f'cat {input_path} | hakrawler -subs -u | grep -Eo {domain_regex} > {results_dir}/urls_hakrawler.txt'
	waybackurls_cmd = f'cat {input_path} | waybackurls | grep -Eo {domain_regex} > {results_dir}/urls_waybackurls.txt'
	gospider_cmd = f'gospider -S {input_path} --js -t 100 -d 2 --sitemap --robots -w -r | grep -Eo {domain_regex} > {results_dir}/urls_gospider.txt'
	tools_cmd_map = {
		'gauplus': gauplus_cmd,
		'hakrawler': hakrawler_cmd,
		'waybackurls': waybackurls_cmd,
		'gospider': gospider_cmd
	}
	cleanup_cmds = [
		f'cat {results_dir}/urls* > {results_dir}/final_urls.txt',
		# f'rm -rf {results_dir}/url*',
		f'cat {results_dir}/endpoints_alive.txt >> {results_dir}/final_urls.txt',
		f'sort -u {results_dir}/final_urls.txt -o {output_path}'
	]
	if ignore_file_extension:
		ignore_exts = '|'.join(ignore_file_extension)
		cleanup_cmds.extend([
			f'cat {output_path} | grep -Eiv "\\.({ignore_exts}).*" > {results_dir}/temp_urls.txt',
			# f'rm {output_path}',
			f'mv {results_dir}/temp_urls.txt {output_path}'
		])

	tasks = group(
		run_system_commands.si(tool_cmd)
		for tool_name, tool_cmd in tools_cmd_map.items()
		if tool_name in tools
	)
	cleanup = chain(run_system_commands.si(cmd) for cmd in cleanup_cmds)
	result = chord(tasks)(cleanup)

	# Wait for tasks to complete as we read from the output path
	with allow_join_result():
		result = result.get()

	# Store all the endpoints and run httpx
	with open(output_path) as f:
		endpoints = f.readlines()

	for url in endpoints:
		http_url = url.strip()
		subdomain_name = get_subdomain_from_url(http_url)
		subdomain, created = Subdomain.objects.get_or_create(
			scan_history=scan_history,
			target_domain=domain,
			name=subdomain_name)
		endpoint, _ = EndPoint.objects.get_or_create(
			scan_history=scan_history,
			target_domain=domain,
			subdomain=subdomain,
			http_url=http_url)
		if created:
			logger.warning(
				f'Added new subdomain {subdomain_name} from HTTP URL {http_url}'
			)
			endpoint.subdomain = subdomain
			endpoint.save()

	if send_output_file:
		send_files_to_discord(output_path)

	# TODO:
	# Go spider & waybackurls accumulates a lot of urls, which is good but
	# nuclei takes a long time to scan even a simple website, so we will do
	# http probing and filter HTTP status 404, this way we can reduce the number
	# of non-existent URLS.
	http_crawl(
		scan_history_id=scan_history_id,
		activity_id=activity_id,
		domain_id=domain_id,
		yaml_configuration=yaml_configuration,
		results_dir=results_dir,
		description='HTTP Crawl')

	# Log endpoint stats
	endpoint_query = (
		EndPoint.objects
		.filter(scan_history__id=scan_history.id)
		.distinct()
	)
	endpoint_count = endpoint_query.count()
	endpoint_alive_count = len([
		ep for ep in endpoint_query.all() if ep.is_alive()
	])

	# Send status notif
	if send_status:
		msg = (
			f'Task "fetch_url" has finished gathering endpoints for {domain.name} '
			f'and has discovered *{endpoint_count}* unique endpoints '
			f'(*{endpoint_alive_count}/{endpoint_count}* alive).'
		)
		send_notification(msg)

	# Run gf patterns on saved endpoints
	# TODO: refactor to Celery workflow
	gf_patterns = config.get(GF_PATTERNS, [])
	for gf_pattern in gf_patterns:
		# TODO: js var is causing issues, removing for now
		if gf_pattern == 'jsvar':
			logger.info('Ignoring jsvar as it is causing issues.')
			continue
		logger.warning(f'Running gf on pattern "{gf_pattern}"')
		output_file = f'{results_dir}/gf_patterns_{gf_pattern}.txt'
		cmd = f'cat {output_path} | gf {gf_pattern} | grep -Eo {domain_regex} >> {output_file} '
		logger.info(cmd)
		os.system(cmd)
		if not os.path.exists(output_file):
			logger.error(f'Could not find GF output file {output_file}. Skipping GF pattern "{gf_pattern}"')
			continue

		# Read output file line by line and
		with open(output_file) as f:
			lines = f.readlines()

		# Add endpoints / subdomains to DB
		for url in lines:
			http_url = url.strip()
			subdomain_name = get_subdomain_from_url(http_url)
			subdomain, created = Subdomain.objects.get_or_create(
				target_domain=domain,
				scan_history=scan_history,
				name=subdomain_name)
			if created:
				logger.warning(f'Found new subdomain {subdomain_name}')
			endpoint, created = EndPoint.objects.get_or_create(
				scan_history=scan_history,
				target_domain=domain,
				subdomain=subdomain,
				http_url=http_url)
			if created:
				logger.warning(f'Found new endpoint {http_url}')
			earlier_pattern = endpoint.matched_gf_patterns
			pattern = f'{earlier_pattern},{pattern}' if earlier_pattern else gf_pattern
			endpoint.matched_gf_patterns = pattern
			endpoint.subdomain = subdomain
			endpoint.save()

@app.task
def vulnerability_scan(
		scan_history_id,
		activity_id,
		domain_id,
		engine_id=None,
		subdomain_id=None,
		yaml_configuration={},
		path=None,
		results_dir=None,
		filename='vulns.json',
		subscan=None,
		description=None):
	"""
	This function will run nuclei as a vulnerability scanner

	Args:
		scan_history (startScan.models.ScanHistory): ScanHistory instance.
		activity_id (int): Activity ID.
		domain_id (int): Domain ID.
		subdomain_id (int): Subdomain ID.
		yaml_configuration (dict): YAML configuration.
		path (str): URL path.
		results_dir (str): Results directory.
		description (str, optional): Task description shown in UI.

	Notes:
	Unfurl the urls to keep only domain and path, will be sent to vuln scan and
	ignore certain file extensions. Thanks: https://github.com/six2dez/reconftw
	"""
	scan_history = ScanHistory.objects.get(pk=scan_history_id)
	domain = Domain.objects.get(pk=domain_id)

	# Config
	cmd = 'nuclei -json'
	input_path = f'{results_dir}/endpoints_alive.txt'
	config = yaml_configuration.get(VULNERABILITY_SCAN, {})
	custom_header = config.get(CUSTOM_HEADER)
	concurrency = config.get(NUCLEI_CONCURRENCY, 0)
	custom_nuclei_template = config.get(NUCLEI_CUSTOM_TEMPLATE, None)
	domain = Domain.objects.get(pk=scan_history.domain.id)
	nuclei_template = config.get(NUCLEI_TEMPLATE, None)
	proxy = get_random_proxy()
	rate_limit = config.get(RATE_LIMIT, 0)
	retries = config.get(RETRIES, 0)
	severities = config.get(NUCLEI_SEVERITY, NUCLEI_DEFAULT_SEVERITIES)
	severities_str = ','.join(severities)
	timeout = config.get(TIMEOUT, 0)
	use_nuclei_conf = config.get(USE_NUCLEI_CONFIG, False)
	output_path = f'{results_dir}/{filename}'

	# Get alive endpoints
	endpoints = get_endpoints(
		domain,
		subdomain_id=subdomain_id,
		scan_history=scan_history,
		is_alive=True,
		path=path,
		write_filepath=input_path)
	endpoints_count = len(endpoints)

	# Send start notification
	notification = Notification.objects.first()
	send_vuln = notification.send_vuln_notif if notification else False
	send_status = notification.send_scan_status_notif if notification else False
	msg = f'Task "vulnerability_scan" (Nuclei) started on {endpoints_count} endpoints'
	logger.warning(msg)
	if send_status:
		send_notification(msg)

	# Build templates
	# logger.info('Updating Nuclei templates ...')
	# os.system('nuclei -update-templates')

	templates = []
	if not (nuclei_template or custom_nuclei_template):
		logger.info(f'Using default nuclei templates {NUCLEI_DEFAULT_TEMPLATES_PATH}.')
		templates.append(NUCLEI_DEFAULT_TEMPLATES_PATH)

	if nuclei_template:
		if ALL in nuclei_template:
			template = NUCLEI_TEMPLATES_PATH
		else:
			template = ','.join(nuclei_template).replace(',', '-t')
		templates.append(template)

	if custom_nuclei_template:
		custom_nuclei_template_paths = [f'{str(elem)}.yaml' for elem in custom_nuclei_template]
		template = ','.join(custom_nuclei_template_paths).replace(',', '-t')
		templates.append(template)

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
	cmd += f' -timeout {str(timeout)}' if timeout > 0 else ''
	for tpl in templates:
		cmd += f' -t {tpl}'

	# Run cmd
	logger.info(cmd)
	results = []
	for line in execute_live(cmd):
		if not isinstance(line, dict):
			continue
		url = line['host']
		subdomain_name = get_subdomain_from_url(url)
		subdomain = Subdomain.objects.get(
			name=subdomain_name,
			scan_history=scan_history)
		vuln_name = line['info'].get('name', '')
		vuln_type = line['type']
		vuln_severity = line['info'].get('severity', 'unknown')
		vuln_severity_id = NUCLEI_SEVERITY_MAP[vuln_severity]
		http_url = line.get('matched-at')
		vulnerability = Vulnerability(
			name=vuln_name,
			type=vuln_type,
			subdomain=subdomain,
			scan_history=scan_history,
			target_domain=domain,
			http_url=http_url,
			severity=vuln_severity_id,
			template=line['template'],
			template_url=line['template-url'],
			template_id=line['template-id'],
			description=line['info'].get('description' ,''),
			matcher_name=line.get('matcher-name', ''),
			curl_command=line.get('curl-command'),
			extracted_results=line.get('extracted-results', []),
			cvss_metrics=line['info'].get('classification', {}).get('cvss-metrics', ''),
			cvss_score=line['info'].get('classification', {}).get('cvss-score'),
			discovered_date=timezone.now(),
			open_status=True
		)
		logger.warning(f'Found {vuln_severity.upper()} vulnerability "{vuln_name}" of type {vuln_type} on {url}')
		vulnerability.save()

		# Get or create EndPoint object
		endpoint, created = EndPoint.objects.get_or_create(
			scan_history=scan_history,
			target_domain=domain,
			subdomain=subdomain,
			http_url=http_url)
		if created:
			logger.warning(f'Found new endpoint {http_url}')
		vulnerability.endpoint = endpoint
		vulnerability.save()

		# Save tags
		tags = line['info'].get('tags') or []
		for tag_name in tags:
			tag, _ = VulnerabilityTags.objects.get_or_create(name=tag_name)
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
			ref, _ = VulnerabilityReference.objects.get_or_create(url=ref_url)
			vulnerability.references.add(ref)
			vulnerability.save()

		# Save subscan id in vulnerability object
		if subscan:
			vulnerability.vuln_subscan_ids.add(subscan)
			vulnerability.save()

		# Save vulnerability object
		vulnerability.save()

		# Send notification for all vulnerabilities except info
		url = vulnerability.http_url or vulnerability.subdomain
		if send_vuln:
			message = f""""*Alert: Vulnerability identified*"

			A *{vuln_severity.upper()}* severity vulnerability has been identified.'

			Vulnerability Name: {vulnerability.name}'
			Vulnerable URL: {vulnerability.host}'
			"""
			send_notification(message)

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
		vulns = Vulnerability.objects.filter(scan_history__id=scan_history.id)
		info_count = vulns.filter(severity=0).count()
		low_count = vulns.filter(severity=1).count()
		medium_count = vulns.filter(severity=2).count()
		high_count = vulns.filter(severity=3).count()
		critical_count = vulns.filter(severity=4).count()
		unknown_count = vulns.filter(severity=-1).count()
		vulnerability_count = info_count + low_count + medium_count + high_count + critical_count + unknown_count
		message = f"""Vulnerability scan has been completed for {domain.name} and {vulnerability_count} vulnerabilities were discovered.

		*Vulnerability stats:*

		Critical: {critical_count}
		High: {high_count}
		Medium: {medium_count}
		Low: {low_count}
		Info: {info_count}
		Unknown: {unknown_count}
		"""
		send_notification(message)


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
def osint(
		scan_history_id,
		activity_id,
		domain_id,
		engine_id=None,
		yaml_configuration={},
		results_dir=None,
		subdomain_id=None,
		path=None,
		description=None):
	"""Run Open-Source Intelligence tools on selected domain.

	Args:
		scan_history (startScan.models.ScanHistory): ScanHistory instance.
		activity_id (int): Activity ID.
		domain_id (int): Domain ID.
		yaml_configuration (dict): YAML configuration.
		results_dir (str): Results directory.
		description (str, optional): Task description shown in UI.
	"""
	config = yaml_configuration.get(OSINT, {})
	scan_history = ScanHistory.objects.get(pk=scan_history_id)
	domain = Domain.objects.get(pk=domain_id)
	notification = Notification.objects.first()
	send_status = notification.send_scan_status_notif if notification else False
	msg = f'OSInt started on {domain.name}'
	logger.warning(msg)
	if send_status:
		send_notification(msg)

	if 'discover' in config:
		osint_discovery(scan_history, domain, yaml_configuration, results_dir)

	if 'dork' in config:
		dorking(scan_history, yaml_configuration)

	msg = f'OSINT completed on {domain.name}'
	logger.warning(msg)
	if send_status:
		send_notification()


def osint_discovery(scan_history, domain, yaml_configuration, results_dir):
	osint_config = yaml_configuration.get(OSINT, {})
	osint_lookup = osint_config.get(OSINT_DISCOVER, OSINT_DEFAULT_LOOKUPS)
	osint_intensity = osint_config.get(INTENSITY, 'normal')
	documents_limit = osint_config.get(OSINT_DOCUMENTS_LIMIT, 50)

	# Get and save meta info
	if 'metainfo' in osint_lookup:
		if osint_intensity == 'normal':
			meta_dict = DottedDict({
				'osint_target': domain.name,
				'domain': domain,
				'scan_id': scan_history,
				'documents_limit': documents_limit
			})
			get_and_save_meta_info(meta_dict)
		elif osint_intensity == 'deep':
			subdomains = Subdomain.objects.filter(scan_history=scan_history)
			for subdomain in subdomains:
				meta_dict = DottedDict({
					'osint_target': subdomain.name,
					'domain': domain,
					'scan_id': scan_history,
					'documents_limit': documents_limit
				})
				get_and_save_meta_info(meta_dict)

	if 'emails' in osint_lookup:
		get_and_save_emails(scan_history, results_dir)
		get_and_save_leaked_credentials(scan_history, results_dir)

	if 'employees' in osint_lookup:
		get_and_save_employees(scan_history, results_dir)

def dorking(scan_history, yaml_configuration):
	# Some dork sources: https://github.com/six2dez/degoogle_hunter/blob/master/degoogle_hunter.sh
	config = yaml_configuration.get(OSINT, {})
	dorks = config.get(OSINT_DORK, DORKS_DEFAULT_NAMES)
	for dork in dorks:
		if dork == 'stackoverflow':
			dork_name = 'site:stackoverflow.com'
			dork_type = 'stackoverflow'
			get_and_save_dork_results(
				dork,
				dork_type,
				scan_history,
				in_target=False
			)

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
				get_and_save_dork_results(
					dork_name[3:],
					dork_type,
					scan_history,
					in_target=False
				)

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
				get_and_save_dork_results(
					dork_name[3:],
					dork_type,
					scan_history,
					in_target=False
				)

		elif dork == 'project_management' :
			dork_type = 'Project Management'
			project_websites = [
				'trello.com',
				'*.atlassian.net'
			]
			dork_name = ''
			for website in project_websites:
				dork_name = dork + ' | ' + 'site:' + website
				get_and_save_dork_results(
					dork_name[3:],
					dork_type,
					scan_history,
					in_target=False
				)

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
				get_and_save_dork_results(
					dork_name[3:],
					dork_type,
					scan_history,
					in_target=False
				)

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
			for extension in config_file_ext:
				dork_name = dork + ' | ' + 'ext:' + extension
				get_and_save_dork_results(
					dork_name[3:],
					dork_type,
					scan_history,
					in_target=True
				)

		if dork == 'jenkins' :
			dork_type = 'Jenkins'
			dork_name = 'intitle:\"Dashboard [Jenkins]\"'
			get_and_save_dork_results(
				dork_name,
				dork_type,
				scan_history,
				in_target=True
			)

		elif dork == 'wordpress_files' :
			dork_type = 'Wordpress Files'
			inurl_lookup = [
				'wp-content',
				'wp-includes'
			]

			dork_name = ''
			for lookup in inurl_lookup:
				dork_name = dork + ' | ' + 'inurl:' + lookup
				get_and_save_dork_results(
					dork_name[3:],
					dork_type,
					scan_history,
					in_target=True
				)

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
				get_and_save_dork_results(
					dork_name[3:],
					dork_type,
					scan_history,
					in_target=False
				)

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
				get_and_save_dork_results(
					dork_name[3:],
					dork_type,
					scan_history,
					in_target=True
				)

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
				get_and_save_dork_results(
					dork_name[3:],
					dork_type,
					scan_history,
					in_target=True
				)

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
				get_and_save_dork_results(
					dork_name[3:],
					dork_type,
					scan_history,
					in_target=True
				)

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
				get_and_save_dork_results(
					dork_name[3:],
					dork_type,
					scan_history,
					in_target=True
				)

		elif dork == 'traefik':
			dork_name = 'intitle:traefik inurl:8080/dashboard'
			dork_type = 'Traefik'
			get_and_save_dork_results(
				dork_name,
				dork_type,
				scan_history,
				in_target=True
			)

		elif dork == 'git_exposed':
			dork_name = 'inurl:\"/.git\"'
			dork_type = '.git Exposed'
			get_and_save_dork_results(
				dork_name,
				dork_type,
				scan_history,
				in_target=True
			)


def get_and_save_dork_results(dork, type, scan_history, in_target=False):
	degoogle_obj = degoogle.dg()
	proxy = get_random_proxy()
	if proxy:
		os.environ['https_proxy'] = proxy
		os.environ['HTTPS_PROXY'] = proxy
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
	return dorks

def get_and_save_employees(scan_history, results_dir):
	theHarvester_dir = '/usr/src/github/theHarvester'
	output_filepath = f'{results_dir}/results.json'
	cmd  = f'cd {theHarvester_dir} && python3 theHarvester.py -d {scan_history.domain.name} -b all -f {output_filepath}'

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
	logger.warning(f'Running theHarvester on {scan_history.domain.name}')
	logger.info(cmd)
	os.system(cmd)

	# Delete proxy environ var
	if 'https_proxy' in os.environ:
		del os.environ['https_proxy']
	if 'HTTPS_PROXY' in os.environ:
		del os.environ['HTTPS_PROXY']

	# Get file location
	if not os.path.isfile(output_filepath):
		logger.error(f'Could not open {output_filepath}')
		return

	# Run headless firefox and parse harvester results with it
	with open(output_filepath, 'r') as f:
		data = json.load(f)

	emails = data.get('emails', [])
	hosts = data.get('hosts', [])
	ips = data.get('ips', [])
	linkedin_people = data.get('linkedin_people', [])
	twitter_people = data.get('twitter_people', [])

	for email_address in emails:
		email, created = Email.objects.get_or_create(address=email_address)
		if created:
			logger.warning(f'Found email address {email_address}')
		scan_history.emails.add(email)
		scan_history.save()

	for people in linkedin_people:
		employee, created = Employee.objects.get_or_create(name=people, designation='linkedin')
		if created:
			logger.warning(f'Found employee {people}')
		scan_history.employees.add(employee)
		scan_history.save()

	for people in twitter_people:
		employee, created = Employee.objects.get_or_create(name=people, designation='twitter')
		if created:
			logger.warning(f'Found employee {people}')
		scan_history.employees.add(employee)
		scan_history.save()

	return {
		'emails': emails,
		'employees': scan_history.employees,
		'hosts': hosts,
		'ips': ips
	}


def get_and_save_emails(scan_history, results_dir):
	emails = []

	# Proxy settings
	proxy = get_random_proxy()
	if proxy:
		os.environ['https_proxy'] = proxy
		os.environ['HTTPS_PROXY'] = proxy

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
	leak_target_path = f'{results_dir}/creds_target.txt'
	with open(leak_target_path, 'w') as leak_target_file:
		for email_address in emails:
			email, _ = Email.objects.get_or_create(address=email_address)
			scan_history.emails.add(email)
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
	logger.warning('Getting leaked credentials')
	leak_target_path = f'{results_dir}/creds_target.txt'
	# TODO: pwndb is dead, long live h8mail !!!
	cmd = f'python3 /usr/src/github/pwndb/pwndb.py --proxy tor:9150 --output json --list {leak_target_path}'
	# leak_output_file = f'{results_dir}/pwndb.json'
	try:
		logger.info(cmd)
		out = subprocess.getoutput(cmd)
		logger.info(out)
		creds = []
		try:
			creds = json.loads(out)
			if not creds:
				logger.error('No leaked credentials found in pwnd output')
		except Exception as e:
			logger.exception(e)
			logger.error('Error parsing pwndb output')
			pass

		for cred in creds:
			if cred['username'] != 'donate':
				email_id = f"{cred['username']}@{cred['domain']}"
				email_obj, _ = Email.objects.get_or_create(
					address=email_id,
				)
				email_obj.password = cred['password']
				email_obj.save()
				scan_history.emails.add(email_obj)
		return creds
	except Exception as e:
		logger.exception(e)
		return


def get_and_save_meta_info(meta_dict):
	logger.warning(f'Getting metadata for {meta_dict.osint_target}')

	# Proxy settngs
	proxy = get_random_proxy()
	if proxy:
		os.environ['https_proxy'] = proxy
		os.environ['HTTPS_PROXY'] = proxy

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
			os=metadata.get('OSInfo', '').rstrip('\x00')
		)
		meta_finder_document.save()
		results.append(meta_finder_document)
	return results


def get_subdomains(target_domain, scan_history=None, write_filepath=None, subdomain_id=None, exclude_subdomains=None, path=None):
	"""Get Subdomain objects from DB.

	Args:
		target_domain (startScan.models.Domain): Target Domain object.
		scan_history (startScan.models.ScanHistory, optional): ScanHistory object.
		write_filepath (str): Write info back to a file.
		subdomain_id (int): Subdomain id.
		exclude_subdomains (bool): Exclude subdomains, only return subdomain matching domain.
		path (str): Add URL path to subdomain.

	Returns:
		list: List of subdomains matching query.
	"""
	base_query = Subdomain.objects.filter(target_domain=target_domain, scan_history=scan_history)
	if subdomain_id:
		base_query = base_query.filter(pk=subdomain_id)
	elif exclude_subdomains:
		base_query = base_query.filter(name=target_domain.name)
	subdomain_query = base_query.distinct('name').order_by('name')
	subdomains = [
		subdomain.name
		for subdomain in subdomain_query.all()
		if subdomain.name
	]
	if not subdomains:
		logger.warning('No subdomains were found in query !')

	if path:
		subdomains = [f'{subdomain}/{path}' for subdomain in subdomains]

	if write_filepath:
		with open(write_filepath, 'w') as f:
			f.write('\n'.join(subdomains))

	return subdomains

def get_endpoints(
		target_domain,
		subdomain_id=None,
		scan_history=None,
		is_alive=False,
		path=None,
		write_filepath=None,
		exclude_subdomains=False):
	"""Get EndPoint objects from DB.

	Args:
		target_domain (startScan.models.Domain): Target Domain object.
		scan_history (startScan.models.ScanHistory, optional): ScanHistory object.
		is_alive (bool): If True, select only alive subdomains.
		path (str): URL path.
		write_filepath (str): Write info back to a file.

	Returns:
		list: List of subdomains matching query.
	"""
	base_query = (
		EndPoint.objects
		.filter(
			scan_history=scan_history,
			target_domain=target_domain,
			http_url__isnull=False)
	)
	if subdomain_id:
		subdomain = Subdomain.objects.get(pk=subdomain_id)
		base_query = base_query.filter(http_url__contains=subdomain.name)
	elif exclude_subdomains:
		base_query = base_query.filter(name=target_domain.name)
	endpoint_query = base_query.distinct('http_url').order_by('http_url')
	endpoints = [
		endpoint
		for endpoint in endpoint_query.all()
		if endpoint.http_url
	]
	if is_alive:
		endpoints = [e for e in endpoints if e.is_alive()]

	# Grab only http_url from endpoint objects
	endpoints = [e.http_url for e in endpoints]

	if not endpoints:
		logger.warning('No endpoints were found in query !')

	if path:
		endpoints = [e for e in endpoints if path in e]

	if write_filepath:
		with open(write_filepath, 'w') as f:
			f.write('\n'.join(endpoints))

	return endpoints

def create_scan_activity(scan_history_id, message, status):
	scan_activity = ScanActivity()
	scan_activity.scan_of = ScanHistory.objects.get(pk=scan_history_id)
	scan_activity.title = message
	scan_activity.time = timezone.now()
	scan_activity.status = status
	scan_activity.save()
	return scan_activity.id

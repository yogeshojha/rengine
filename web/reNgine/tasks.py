import csv
import json
import os
import random
import subprocess
from datetime import datetime
from time import sleep

import validators
import whatportis
import yaml
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

'''
	All the background tasks to be executed in celery will be here
'''

@app.task
def run_system_commands(system_command):
	'''
		This function will run system commands in celery container
	'''
	os.system(system_command)


@app.task
def initiate_subtask(
		subdomain_id,
		scan_type,
		engine_id=None,
	):
	logger.info('Initiating Subtask')

	# TODO: OSINT IS NOT Currently SUPPORTED!, make it available in later releases
	if scan_type == 'osint':
		logger.warning('OSInt not supported yet. Skipping.')
		return

	# Get scan history and yaml Configuration for this subdomain
	subdomain = Subdomain.objects.get(id=subdomain_id)
	scan_history = ScanHistory.objects.get(id=subdomain.scan_history.id)

	# Create scan activity of SubScan Model
	subscan = SubScan(
		start_scan_date=timezone.now(),
		celery_id=initiate_subtask.request.id,
		scan_history=scan_history,
		subdomain=subdomain,
		type=scan_type,
		status=INITIATED_TASK
	)
	subscan.save()

	if engine_id:
		engine = EngineType.objects.get(id=engine_id)
	else:
		engine = EngineType.objects.get(id=scan_history.scan_type.id)
	config = engine.yaml_configuration

	subscan.engine = engine
	subscan.save()

	results_dir = f'/usr/src/scan_results/{scan_history.results_dir}'
	timestr = datetime.strftime(timezone.now(), '%Y_%m_%d_%H_%M_%S')
	scan_name = f'{subdomain.name}_{timestr}'

	# Create results directory
	if not os.path.exists(results_dir):
		os.mkdir(results_dir)

	# Run subscan
	try:
		yaml_configuration = yaml.load(
			config,
			Loader=yaml.FullLoader)

		subscan.status = RUNNING_TASK
		subscan.save()

		if scan_type == 'port_scan':
			filename = f'ports_{scan_name}.json'
			scan_history.port_scan = True
			scan_history.save()
			port_scan(
				scan_history,
				0,
				yaml_configuration,
				results_dir,
				subdomain=subdomain.name,
				filename=filename,
				subscan=subscan
			)
		elif scan_type == 'dir_fuzz':
			filename = f'dir_fuzz_{scan_name}.json'
			scan_history.dir_file_fuzz = True
			scan_history.save()
			directory_fuzz(
				scan_history,
				0,
				yaml_configuration,
				results_dir,
				subdomain=subdomain.name,
				filename=filename,
				subscan=subscan
			)
		elif scan_type == 'endpoint':
			filename = f'endpoints_{scan_name}.txt'
			scan_history.fetch_url = True
			scan_history.save()
			fetch_endpoints(
				scan_history,
				0,
				yaml_configuration,
				results_dir,
				subdomain=subdomain,
				filename=filename,
				subscan=subscan
			)
		elif scan_type == 'vulnerability_scan':
			filename = f'vuln_{scan_name}.txt'
			scan_history.vulnerability_scan = True
			scan_history.save()
			vulnerability_scan(
				scan_history,
				0,
				yaml_configuration,
				results_dir,
				subdomain=subdomain,
				filename=filename,
				subscan=subscan
			)
		else:
			logger.error(f'Scan type "{scan_type}" is not supported yet.')

		task_status = SUCCESS_TASK

	except Exception as e:
		logger.exception(e)
		task_status = FAILED_TASK
		subscan.error_message = str(e)
	finally:
		subscan.stop_scan_date = timezone.now()
		subscan.status = task_status
		subscan.save()


@app.task
def initiate_scan(
		domain_id,
		scan_history_id,
		scan_type,
		engine_type,
		imported_subdomains=None,
		out_of_scope_subdomains=[],
		results_dir='/usr/src/scan_results'):


	if scan_type == 1: # immediate
		task = ScanHistory()
		task.scan_status = -1
	elif scan_type == 0: # scheduled
		task = ScanHistory.objects.get(pk=scan_history_id)

	# Get engine
	engine = EngineType.objects.get(pk=engine_type)

	# Get domain and set last_scan_date
	domain = Domain.objects.get(pk=domain_id)
	domain.last_scan_date = timezone.now()
	domain.save()

	# Once the celery task starts, change the task status to started
	task.scan_type = engine
	task.celery_id = initiate_scan.request.id
	task.domain = domain
	task.scan_status = 1
	task.start_scan_date = timezone.now()
	# TODO: modify this; it should read something like
	# task.tasks = engine.tasks for it to work dynamically
	task.subdomain_discovery = engine.subdomain_discovery
	task.waf_detection = engine.waf_detection
	task.dir_file_fuzz = engine.dir_file_fuzz
	task.port_scan = engine.port_scan
	task.fetch_url = engine.fetch_url
	task.osint = engine.osint
	task.screenshot = engine.screenshot
	task.vulnerability_scan = engine.vulnerability_scan
	task.save()

	# Send start notif
	notification = Notification.objects.first()
	send_status = notification.send_scan_status_notif if notification else False
	if send_status:
		send_notification(f'reNgine has initiated recon for target {domain.name} with engine type {engine.engine_name}')

	# Create results directory
	os.chdir(results_dir)
	timestr = datetime.strftime(timezone.now(), '%Y_%m_%d_%H_%M_%S')
	current_scan_dir = f'{domain.name}_{timestr}'
	os.mkdir(current_scan_dir)
	task.results_dir = current_scan_dir
	task.save()

	# Load YAML config
	yaml_configuration = yaml.load(
		task.scan_type.yaml_configuration,
		Loader=yaml.FullLoader)

	'''
	Add GF patterns name to db for dynamic URLs menu
	'''
	gf_patterns = yaml_configuration.get(GF_PATTERNS, [])
	if engine.fetch_url and gf_patterns:
		task.used_gf_patterns = ','.join(gf_patterns)
		task.save()

	results_dir = f'{results_dir}/{current_scan_dir}'

	# Put all imported subdomains into txt file and also in Subdomain model
	if imported_subdomains:
		extract_imported_subdomain(
			imported_subdomains, task, domain, results_dir)

	'''
	a target in itself is a subdomain, some tool give subdomains as
	www.yogeshojha.com but url and everything else resolves to yogeshojha.com
	In that case, we would already need to store target itself as subdomain
	'''
	initial_subdomain_file = 'target_domain.txt' if task.subdomain_discovery else 'sorted_subdomain_collection.txt'
	subdomain_file = f'{results_dir}/{initial_subdomain_file}'
	with open(subdomain_file, "w") as f:
		f.write(domain.name + "\n")

	try:
		scan_id = create_scan_activity(task, "Scanning Started", 2)
		if task.subdomain_discovery:
			task_id = create_scan_activity(task, "Subdomain Scanning", 1)
			subdomain_scan(
				task,
				domain,
				yaml_configuration,
				results_dir,
				task_id,
				out_of_scope_subdomains)
			update_last_activity(task_id, 2)
		else:
			skip_subdomain_scan(
				task,
				domain,
				results_dir)

		# TODO: if task.http_crawl:
		task_id = create_scan_activity(task, "HTTP Crawler", 1)
		http_crawler(
			task,
			domain,
			yaml_configuration,
			results_dir,
			task_id)
		update_last_activity(task_id, 2)

		if task.waf_detection:
			task_id = create_scan_activity(task, "Detecting WAF", 1)
			check_waf(task, results_dir)
			update_last_activity(task_id, 2)

		if task.screenshot:
			task_id = create_scan_activity(task, "Visual Recon - Screenshot", 1)
			grab_screenshot(
				task,
				domain,
				yaml_configuration,
				current_scan_dir,
				task_id)
			update_last_activity(task_id, 2)

		if task.port_scan:
			task_id = create_scan_activity(task, "Port Scanning", 1)
			port_scan(
				task,
				task_id,
				yaml_configuration,
				results_dir,
				domain)
			update_last_activity(task_id, 2)

		if task.osint:
			task_id = create_scan_activity(task, "OSINT Running", 1)
			perform_osint(
				task,
				domain,
				yaml_configuration,
				results_dir)
			update_last_activity(task_id, 2)

		if task.dir_file_fuzz:
			task_id = create_scan_activity(task, "Directory Search", 1)
			directory_fuzz(
				task,
				task_id,
				yaml_configuration,
				results_dir,
				domain=domain,
			)
			update_last_activity(task_id, 2)

		if task.fetch_url:
			task_id = create_scan_activity(task, "Fetching endpoints", 1)
			fetch_endpoints(
				task,
				task_id,
				yaml_configuration,
				results_dir,
				domain=domain,
				)
			update_last_activity(task_id, 2)

		if task.vulnerability_scan:
			task_id = create_scan_activity(task, "Vulnerability scan", 1)
			vulnerability_scan(
				task,
				task_id,
				yaml_configuration,
				results_dir,
				domain=domain,
			)
			update_last_activity(task_id, 2)

	except Exception as e:
		logger.exception(e)
		update_last_activity(scan_id, 0, error_message=str(e))
		update_last_activity(task_id, 0, error_message=str(e))
		scan_failed(task)
		task.error_message = str(e)
		task.save()

	create_scan_activity(task, "Scan completed", 2)
	if send_status:
		send_notification(f'*Scan completed*\nreNgine has finished performing recon on target {domain.name}.')

	# Set task's scan_status and save Task to DB
	if ScanActivity.objects.filter(scan_of=task).filter(status=0).all():
		task.scan_status = 0
	else:
		task.scan_status = 2
	task.stop_scan_date = timezone.now()
	task.save()
	return {"status": True}


def skip_subdomain_scan(task, domain, results_dir):
	subdomain_query = Subdomain.objects.filter(scan_history=task, name=domain.name)
	if not subdomain_query.exists():
		subdomain_dict = DottedDict({
			'name': domain.name,
			'scan_history': task,
			'target_domain': domain
		})
		save_subdomain(subdomain_dict)

	# Save target domain to file
	with open(f'{results_dir}/target_domain.txt', 'w+') as file:
		file.write(domain.name + '\n')

	# Add domain to subdomain collection
	os.system(f'cat {results_dir}/target_domain.txt > {results_dir}/subdomain_collection.txt')
	os.system(f'cat {results_dir}/from_imported.txt > {results_dir}/subdomain_collection.txt')
	os.system(f'rm -f {results_dir}/from_imported.txt')
	os.system(f'sort -u {results_dir}/subdomain_collection.txt -o {results_dir}/sorted_subdomain_collection.txt')
	os.system(f'rm -f {results_dir}/subdomain_collection.txt')


def extract_imported_subdomain(imported_subdomains, task, domain, results_dir):
	subdomains = list(set([
		subdomain for subdomain in imported_subdomains
		if validators.domain(subdomain) and domain.name == get_domain_from_subdomain(subdomain)
	]))
	with open(f'{results_dir}/from_imported.txt', 'w+') as file:
		for subdomain in subdomains:
			subdomain = subdomain.strip()
			subdomain_query = Subdomain.objects.filter(scan_history=task, name=subdomain)
			if not subdomain_query.exists():
				subdomain_dict = DottedDict({
					'scan_history': task,
					'target_domain': domain,
					'name': subdomain,
					'is_imported_subdomain': True
				})
				save_subdomain(subdomain_dict)
				file.write('{}\n'.format(subdomain))


def subdomain_scan(
		task,
		domain,
		yaml_configuration,
		results_dir,
		activity_id,
		out_of_scope_subdomains=None,
		subscan=None
	):
	"""
	Uses a set of tools (see DEFAULT_SUBDOMAIN_SCAN_TOOLS) to scan all subdomains associated with a domain.
	"""

	# Config
	config = yaml_configuration[SUBDOMAIN_DISCOVERY]
	output_path = f'{results_dir}/sorted_subdomain_collection.txt'
	threads = config.get(THREADS, 20)
	tools = config.get(USES_TOOLS, [])
	default_subdomain_tools = [tool.name.lower() for tool in InstalledExternalTool.objects.filter(is_default=True).filter(is_subdomain_gathering=True)]
	custom_subdomain_tools = [tool.name.lower() for tool in InstalledExternalTool.objects.filter(is_default=False).filter(is_subdomain_gathering=True)]

	# Send start notif
	notification = Notification.objects.first()
	send_status = notification.send_scan_status_notif if notification else False
	send_scan_output = notification.send_scan_output_file if notification else False
	send_subdomain_changes = notification.send_subdomain_changes_notif if notification else False
	send_interesting = notification.send_interesting_notif if notification else False
	msg = f'Subdomain scan started for {domain.name}'
	logger.info(msg)
	if send_status:
		send_notification(msg)

	# Gather tools to run for subdomain scan
	if ALL in tools:
		tools = DEFAULT_SUBDOMAIN_SCAN_TOOLS + custom_subdomain_tools
	tools = [t.lower() for t in tools]

	# Gather threads
	try:
		for tool in tools:
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

			elif tool.lower() in custom_subdomain_tools:
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

	except Exception as e:
		logger.error(e)

	# Gather all the tools' results in one single file. wrote subdomains into separate files,
	# cleanup tool results and sort all subdomains.
	os.system(f'cat {results_dir}/*.txt > {results_dir}/subdomain_collection.txt')
	os.system(f'cat {results_dir}/target_domain.txt >> {results_dir}/subdomain_collection.txt')
	os.system(f'rm -f {results_dir}/from*')
	os.system(f'sort -u {results_dir}/subdomain_collection.txt -o {results_dir}/sorted_subdomain_collection.txt')
	os.system(f'rm -f {results_dir}/subdomain_collection.txt')

	# Parse the subdomain list file and store in db.
	with open(output_path) as f:
		lines = f.readlines()

	for subdomain in lines:
		subdomain_query = Subdomain.objects.filter(scan_history=task, name=subdomain)
		valid_domain = validators.domain(subdomain)
		included_domain = subdomain not in out_of_scope_subdomains
		if not subdomain_query.exists() and valid_domain and included_domain:
			subdomain_dict = DottedDict({
				'scan_history': task,
				'target_domain': domain,
				'name': subdomain
			})
			save_subdomain(subdomain_dict)

	# Send notifications
	subdomains_count = Subdomain.objects.filter(scan_history=task).count()
	msg = f'Subdomain scan finished with {tools} for {domain.name} and *{subdomains_count}* subdomains were found'
	logger.info(msg)
	if send_status:
		send_notification(msg)

	if send_scan_output:
		send_files_to_discord(f'{results_dir}/sorted_subdomain_collection.txt')

	if send_subdomain_changes:
		added_subdomains = get_new_added_subdomain(task.id, domain.id)
		removed_subdomains = get_removed_subdomain(task.id, domain.id)

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
		interesting_subdomains = get_interesting_subdomains(task.id, domain.id)
		if interesting_subdomains:
			message = f'**{interesting_subdomains.count()} interesting subdomains found on domain {domain.name}**'
			subdomains_str = '\n'.join([f'• {subdomain}' for subdomain in removed_subdomains])
			message += subdomains_str
			send_notification(message)


def get_new_added_subdomain(scan_id, domain_id):
	scan_history = ScanHistory.objects.filter(domain=domain_id).filter(subdomain_discovery=True).filter(id__lte=scan_id)
	if not scan_history.count() > 1:
		return
	last_scan = scan_history.order_by('-start_scan_date')[1]
	scanned_host_q1 = Subdomain.objects.filter(scan_history__id=scan_id).values('name')
	scanned_host_q2 = Subdomain.objects.filter(scan_history__id=last_scan.id).values('name')
	added_subdomain = scanned_host_q1.difference(scanned_host_q2)
	return Subdomain.objects.filter(scan_history=scan_id).filter(name__in=added_subdomain)


def get_removed_subdomain(scan_id, domain_id):
	scan_history = ScanHistory.objects.filter(domain=domain_id).filter(subdomain_discovery=True).filter(id__lte=scan_id)
	if not scan_history.count() > 1:
		return
	last_scan = scan_history.order_by('-start_scan_date')[1]
	scanned_host_q1 = Subdomain.objects.filter(scan_history__id=scan_id).values('name')
	scanned_host_q2 = Subdomain.objects.filter(scan_history__id=last_scan.id).values('name')
	removed_subdomains = scanned_host_q2.difference(scanned_host_q1)
	return Subdomain.objects.filter(scan_history=last_scan).filter(name__in=removed_subdomains)


def http_crawler(task, domain, yaml_configuration, results_dir, activity_id, threads=100):
	"""
	Uses httpx to crawl domain for important info like page titles, http status, etc...
	"""
	cmd = '/go/bin/httpx'
	custom_header = yaml_configuration.get(CUSTOM_HEADER)
	alive_subdomain_file = open(f'{results_dir}/alive.txt', 'w')
	httpx_results_file = f'{results_dir}/httpx.json'
	subdomain_scan_results_file = f'{results_dir}/sorted_subdomain_collection.txt'
	proxy = get_random_proxy()

	# Send notification
	notification = Notification.objects.first()
	send_status = notification.send_scan_status_notif if notification else False
	msg = f'httpx HTTP Crawler has started for {domain.name}'
	logger.info(msg)
	if send_status:
		send_notification(msg)

	cmd += f' -status-code -content-length -title -tech-detect -cdn -ip -follow-host-redirects -random-agent -t {threads}'
	cmd += f' --http-proxy {proxy}' if proxy else ''
	cmd += f' -H "{custom_header}"' if custom_header else ''
	cmd += f' -json -l {subdomain_scan_results_file}'

	# Run command
	logger.info(f'Running httpx scan on {domain} ...')
	cmd = remove_cmd_injection_chars(cmd)
	logger.info(cmd)
	results = []
	for line in execute_live(cmd):
		if not isinstance(line, dict):
			continue
		try:
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
				subdomain, _ = Subdomain.objects.get_or_create(scan_history=task, name=line['input'].strip())
			else:
				subdomain, _ = Subdomain.objects.get_or_create(scan_history=task, name=http_url.split("//")[-1].strip())
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
			endpoint = EndPoint(
				scan_history=task,
				target_domain=domain,
				subdomain=subdomain,
				discovered_date=discovered_date,
				is_default=True,
				http_url=http_url,
				http_status=http_status,
				page_title=page_title,
				content_length=content_length,
				webserver=webserver,
				response_time=response_time
			)
			endpoint.save()

			# Add alive endpoint URLs to file
			if endpoint.is_alive():
				alive_subdomain_file.write(endpoint.http_url + '\n')

			# Add technology objects to DB
			technologies = line.get('technologies', [])
			for technology in technologies:
				if Technology.objects.filter(name=technology).exists():
					tech = Technology.objects.get(name=technology)
				else:
					tech = Technology(name=technology)
					tech.save()
				subdomain.technologies.add(tech)
				endpoint.technologies.add(tech)
				subdomain.save()
				endpoint.save()

			# Add ip objects to DB
			a_records = line.get('a', [])
			for ip_address in a_records:
				if IpAddress.objects.filter(address=ip_address).exists():
					ip = IpAddress.objects.get(address=ip_address)
				else:
					ip = IpAddress(address=ip_address)
					ip.is_cdn = line.get('cdn', False)
				ip.save()

				# Add CountryISO to DB
				subprocess_output = subprocess.getoutput(['geoiplookup {}'.format(ip_address)])
				if 'IP Address not found' not in subprocess_output and "can't resolve hostname" not in subprocess_output:
					country_iso = subprocess_output.split(':')[1].strip().split(',')[0]
					country_name = subprocess_output.split(':')[1].strip().split(',')[1].strip()
					iso_object, _ = CountryISO.objects.get_or_create(
						iso=country_iso,
						name=country_name
					)
					ip.geo_iso = iso_object

				ip.save()
				subdomain.ip_addresses.add(ip)
				subdomain.save()

			# Add IP object in DB
			if host:
				if IpAddress.objects.filter(address=host).exists():
					ip = IpAddress.objects.get(address=host)
				else:
					ip = IpAddress(address=host)
					ip.is_cdn = line.get('cdn', False)
				ip.save()

				# Add geo iso
				subprocess_output = subprocess.getoutput(['geoiplookup {}'.format(host)])
				if 'IP Address not found' not in subprocess_output and "can't resolve hostname" not in subprocess_output:
					country_iso = subprocess_output.split(':')[1].strip().split(',')[0]
					country_name = subprocess_output.split(':')[1].strip().split(',')[1].strip()
					iso_object, _ = CountryISO.objects.get_or_create(
						iso=country_iso,
						name=country_name
					)
					ip.geo_iso = iso_object
				ip.save()

			# Save subdomain and endpoint
			subdomain.save()
			endpoint.save()

		except Exception as exception:
			logger.exception(exception)
			continue

	# Close file handle
	alive_subdomain_file.close()

	# Write results to JSON file
	with open(httpx_results_file, 'w') as f:
		json.dump(results, f)

	# Send finish notification
	if send_status:
		alive_count = Subdomain.objects.filter(scan_history__id=task.id).values('name').distinct().filter(http_status__exact=200).count()
		send_notification(f'httpx HTTP crawler has finished for {domain.name} and {alive_count} subdomains were marked as "alive".')

def geo_localize(host):
	"""
	Uses geoiplookup to find location associated with host.
	"""
	cmd = f'geoiplookup {host}'
	out = subprocess.getoutput([cmd])
	if 'IP Address not found' not in out and "can't resolve hostname" not in out:
		country_iso = out.split(':')[1].strip().split(',')[0]
		country_name = out.split(':')[1].strip().split(',')[1].strip()
		CountryISO.objects.get_or_create(
			iso=country_iso,
			name=country_name
		)

def grab_screenshot(task, domain, yaml_configuration, results_dir, activity_id):
	"""
	Uses EyeWitness to gather screenshot of a domain and/or url.
	"""

	# Config
	screenshots_path = f'{results_dir}/screenshots'
	result_csv_path = f'{results_dir}/screenshots/Requests.csv'
	alive_subdomains_path = f'{results_dir}/alive.txt'
	timeout = yaml_configuration.get(SCREENSHOT, {}).get(TIMEOUT, 0)
	threads = yaml_configuration.get(SCREENSHOT, {}).get(THREADS, 0)

	# Build cmd
	cmd = f'python3 /usr/src/github/EyeWitness/Python/EyeWitness.py -f {alive_subdomains_path} -d {screenshots_path} --no-prompt'
	cmd += f' --timeout {timeout}' if timeout > 0 else ''
	cmd += f' --threads {threads}' if threads > 0 else ''

	# Send start notif
	notification = Notification.objects.first()
	send_status = notification.send_scan_status_notif if notification else False
	if send_status:
		send_notification(f'EyeWitness has started gathering screenshots of {domain.name}')

	# Run cmd
	logger.info(cmd)
	process = subprocess.Popen(cmd.split())
	process.wait()
	if not os.path.isfile(result_csv_path):
		logger.error (f'Could not load EyeWitness results at {result_csv_path} for {domain.name}.')
		return

	# Loop through results and save objects in DB
	logger.info(f'Gathering EyeWitness results from {result_csv_path} ...')
	with open(result_csv_path, 'r') as file:
		reader = csv.reader(file)
		for row in reader:
			one, two, three, name, status, path = tuple(row)
			logger.info(f'{one}:{two}:{three}:{name}:{status}:{path}')
			subdomain_query = Subdomain.objects.filter(scan_history__id=task.id).filter(name=name)
			if status == 'Successful' and subdomain_query.exists():
				subdomain = subdomain_query.first()
				subdomain.screenshot_path = path.replace('/usr/src/scan_results/', '')
				subdomain.save()
				logger.info(f'Added screenshot for {subdomain.name} to DB')

	# Remove all db, html extra files in screenshot results
	os.system('rm -rf {0}/*.csv {0}/*.db {0}/*.js {0}/*.html {0}/*.css'.format(screenshots_path))
	os.system(f'rm -rf {screenshots_path}/source')

	# Send finish notif
	if send_status:
		send_notification(f'EyeWitness has finished gathering screenshots of {domain.name}')

def port_scan(
		scan_history,
		activity_id,
		yaml_configuration,
		results_dir,
		domain=None,
		subdomain=None,
		filename='ports.json',
		subscan=None
	):
	'''
	This function is responsible for running the port scan
	'''
	cmd = 'naabu -json -exclude-cdn'
	config = yaml_configuration[PORT_SCAN]
	exclude_ports = config.get(EXCLUDE_PORTS, [])
	ports = config.get(PORTS, NAABU_DEFAULT_PORTS)
	naabu_rate = config.get(NAABU_RATE, 0)
	use_naabu_config = config.get(USE_NAABU_CONFIG, False)
	domain_name = domain.name if domain else subdomain
	subdomains_path = f'{results_dir}/sorted_subdomain_collection.txt'
	exclude_ports_str = ','.join(exclude_ports)

	# Random sleep to prevent ip and port being overwritten
	sleep(random.randint(1,5))

	# Send start notif
	notification = Notification.objects.first()
	send_status = notification.send_scan_status_notif if notification else False
	send_output_file = notification.send_scan_output_file if notification else False
	if send_status:
		send_notification(f'naabu has started gathering ports info for {domain_name}.')

	# Build CMD
	if domain:
		cmd += f' -list {subdomains_path}'
	elif subdomain:
		cmd += f' -host {subdomain}'
	else:
		raise ValueError('domain or subdomain must be set')

	if 'full' in ports:
		ports_str = ' -p -'
	elif 'top-100' in ports:
		ports_str = ' -top-ports 100 '
	elif 'top-1000' in ports:
		ports_str = ' -top-ports 1000'
		ports_str = ' -top-ports 1000'
	else:
		ports_str = ','.join(ports)
		ports_str = f' -p {ports_str}'

	cmd += ports_str
	cmd += f' -exclude-ports {exclude_ports_str}' if exclude_ports else ''
	cmd += f' -rate {naabu_rate} ' if naabu_rate > 0 else ''
	cmd += ' -config /root/.config/naabu/config.yaml ' if use_naabu_config else ''

	# Writing port results
	try:
		logger.info(f'Running naabu port scan on {domain_name}')
		logger.info(cmd)
		for line in execute_live(cmd):
			if not isinstance(line, dict):
				continue
			port_number = line['port']
			ip_address = line['ip']
			host = line['host']

			# Add port to DB
			port_query = Port.objects.filter(number__exact=port_number)
			if port_query.exists():
				port = Port.objects.get(number=port_number)
			else:
				port = Port()
				port.number = port_number
				port.is_uncommon = port_number in UNCOMMON_WEB_PORTS
				port_details = whatportis.get_ports(str(port_number))
				if len(port_details) > 0:
					port.service_name = port_details[0].name
					port.description = port_details[0].description
				port.save()
				logger.info(f'Found port {port.number} ({port.service_name} - {port.description}) in {host}.')

			# Add IP DB
			ip_query = IpAddress.objects.filter(address=ip_address)
			if ip_query.exists():
				ip = ip_query.first()
			else:
				ip = IpAddress()
				ip.address = ip_address
				ip.save()
			ip.ports.add(port)
			ip.save()
			if subscan:
				ip.ip_subscan_ids.add(subscan)
				ip.save()

			# Add IP to Subdomain in DB
			subdomain_query = Subdomain.objects.filter(name=host, scan_history=scan_history, ip_addresses__address=ip_address)
			if subdomain_query.exists():
				subdomain = subdomain_query.first()
				subdomain.ip_addresses.add(ip)
				subdomain.save()

	except Exception as e:
		logger.exception(e)
		if not subscan:
			update_last_activity(activity_id, 0)

	if send_status:
		port_query = (
			Port.objects
			.filter(ports__in=IpAddress.objects
				.filter(ip_addresses__in=Subdomain.objects
					.filter(scan_history__id=scan_history.id)
				)
			).distinct()
		)
		port_count = port_query.count()
		send_notification(f'naabu has finished gathering ports info on {domain_name} and has identified {port_count} ports.')

	if send_output_file:
		send_files_to_discord(f'{results_dir}/ports.json')


def check_waf(scan_history, results_dir):
	"""
	Uses wafw00f to check for the presence of a WAP.
	"""
	cmd = 'wafw00f'
	alive_subdomain_path = f'{results_dir}/alive.txt'
	output_path = f'{results_dir}/wafw00f.txt'

	if not os.path.isfile(alive_subdomain_path):
		logger.error(f'Could not find {alive_subdomain_path}')
		return

	cmd += f' -i {alive_subdomain_path} -o {output_path}'
	logger.info(cmd)
	process = subprocess.Popen(cmd.split())
	process.wait()

	if not os.path.isfile(output_path):
		logger.error(f'Could not find {output_path}')
		return

	with open(output_path) as file:
		lines = file.readlines()

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
		waf_query = Waf.objects.filter(name=waf_name, manufacturer=waf_manufacturer)
		if waf_query.exists():
			waf_obj = waf_query.first()
		else:
			waf_obj = Waf(
				name=waf_name,
				manufacturer=waf_manufacturer
			)
			waf_obj.save()

		# Add waf info to Subdomain in DB
		subdomain_query = Subdomain.objects.filter(scan_history=scan_history, http_url=http_url)
		if subdomain_query.exists():
			subdomain = subdomain_query.first()
			subdomain.waf.add(waf_obj)
		subdomain.save()


def directory_fuzz(
		scan_history,
		activity_id,
		yaml_configuration,
		results_dir,
		domain=None,
		subdomain=None,
		filename='dirs.json',
		subscan=None
	):
	"""This function is responsible for performing directory scan, and currently
	uses ffuf as a default tool.
	"""

	# Config
	cmd = 'ffuf'
	output_path = f'{results_dir}/{filename.strip()}'
	domain_name = domain.name if domain else subdomain
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
	if send_status:
		send_notification(f'ffuf directory bruteforce has started for {domain_name}.')

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
	if domain:
		subdomains_fuzz = Subdomain.objects.filter(scan_history__id=scan_history.id).exclude(http_url__isnull=True)
	else:
		subdomains_fuzz = Subdomain.objects.filter(name=subdomain).filter(scan_history__id=scan_history.id)


	# Loop through subdomains and run command
	for subdomain in subdomains_fuzz:
		final_cmd = cmd

		# Delete any existing dirs.json
		if os.path.isfile(output_path):
			os.system(f'rm -rf {output_path}')

		# HTTP URL
		http_url = subdomain.http_url or subdomain.name
		http_url = http_url.strip()
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
		logger.info(final_cmd)
		process = subprocess.Popen(final_cmd.split())
		process.wait()

		try:
			if not os.path.isfile(output_path):
				logger.error(f'Could not read output file "{output_path}"')
				return

			with open(output_path, "r") as f:
				data = json.load(f)

			if not data:
				logger.error(f'No input data was found in {output_path}')
				return

			subdomain = Subdomain.objects.get(scan_history__id=scan_history.id, http_url=subdomain.http_url)
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
					logger.error('FUZZ not found for "{url}"')
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

			if subscan:
				directory_scan.dir_subscan_ids.add(subscan)

			directory_scan.save()
			subdomain.directories.add(directory_scan)
			subdomain.save()

		except Exception as exception:
			logger.error(exception)
			if not subscan:
				update_last_activity(activity_id, 0)
			raise Exception(exception)

	if send_status:
		send_notification(f'ffuf directory bruteforce has finished for {domain_name}')


def fetch_endpoints(
		scan_history,
		activity_id,
		yaml_configuration,
		results_dir,
		domain=None,
		subdomain=None,
		filename='all_urls.txt',
		subscan=None
	):
	"""
	This function is responsible for fetching all the urls associated with target
	and runs HTTP probe.

	reNgine has ability to fetch deep urls, meaning url for all the subdomains,
	but when a subdomain is given, subtask is running, deep or normal scan should
	not work, it should simply fetch urls for that subdomain.
	"""

	# Config
	config = yaml_configuration[FETCH_URL]
	gf_patterns = config.get(GF_PATTERNS, [])
	ignore_file_extension = config.get(IGNORE_FILE_EXTENSION, [])
	scan_intensity = config.get(INTENSITY, DEFAULT_ENDPOINT_SCAN_INTENSITY)
	tools = config.get(USES_TOOLS, DEFAULT_ENDPOINT_SCAN_TOOLS)
	custom_header = yaml_configuration.get(CUSTOM_HEADER)
	domain_name = domain.name if domain else subdomain
	proxy = get_random_proxy()
	output_path = f'{results_dir}/{filename}'
	alive_subdomains_path = output_path
	sorted_subdomains_path = f'{results_dir}/sorted_subdomain_collection.txt'

	# Combine old gf patterns with new ones
	if gf_patterns:
		scan_history.used_gf_patterns = ','.join(gf_patterns)
		scan_history.save()

	# Start notif
	notification = Notification.objects.first()
	send_status = notification.send_scan_status_notif if notification else False
	send_output_file = notification.send_scan_output_file if notification else False
	if send_status:
		send_notification(f'reNgine is currently gathering endpoints for {domain_name}')

	# Run endpoint scanning with multiple tools
	logger.info('Initiated endpoint scanning ...')
	domain_regex = f"\'https?://([a-z0-9]+[.])*{domain_name}.*\'"
	input_target = ''

	for tool in tools:
		try:
			cmd = 'gospider'

			if tool in ('gauplus', 'hakrawler', 'waybackurls'):
				if subdomain:
					subdomain_url = subdomain.http_url if subdomain.http_url else f'https://{subdomain.name}'
					input_target = f'echo {subdomain_url}'
				elif scan_intensity == 'deep' and domain:
					input_target = f'cat {sorted_subdomains_path}'
				else:
					input_target = f'echo {domain_name}'

			if tool == 'gauplus':
				logger.info('Running Gauplus')
				cmd = f'{input_target} | gauplus --random-agent | grep -Eo {domain_regex} > {results_dir}/urls_gau.txt'
				logger.info(cmd)
				os.system(cmd)

			elif tool == 'hakrawler':
				logger.info('Running hakrawler')
				cmd = f'{input_target} | hakrawler -subs -u | grep -Eo {domain_regex} > {results_dir}/urls_hakrawler.txt'
				logger.info(cmd)
				os.system(cmd)

			elif tool == 'waybackurls':
				logger.info('Running waybackurls')
				cmd = f'{input_target} | waybackurls | grep -Eo {domain_regex} > {results_dir}/urls_waybackurls.txt'
				logger.info(cmd)
				os.system(cmd)

			elif tool == 'gospider':
				logger.info('Running gospider')
				if subdomain:
					subdomain_url = subdomain.http_url if subdomain.http_url else f'https://{subdomain.name}'
					cmd += f' -s {subdomain_url}'
				elif scan_intensity == 'deep' and domain:
					cmd += f' -S {alive_subdomains_path}'
				else:
					cmd += f' -s https://{domain_name} '

				cmd += f' --js -t 100 -d 2 --sitemap --robots -w -r | grep -Eo {domain_regex} > {results_dir}/urls_gospider.txt'

			logger.info(cmd)
			os.system(cmd)
		except Exception as e:
			logger.error(f'{tool} exited with an error code.')
			logger.exception(e)
			continue

	# Cleanup urls files
	os.system(f'cat {results_dir}/urls* > {results_dir}/final_urls.txt')
	os.system(f'rm -rf {results_dir}/url*')

	# Sorting and unique urls
	logger.info("Sort and Unique")
	if domain:
		os.system(f'cat {results_dir}/alive.txt >> {results_dir}/final_urls.txt')
	os.system(f'sort -u {results_dir}/final_urls.txt -o {output_path}')

	if ignore_file_extension:
		ignore_extension = '|'.join(ignore_file_extension)
		logger.info('Ignore extensions ' + ignore_extension)
		os.system(f'cat {output_path} | grep -Eiv "\\.({ignore_extension}).*" > {results_dir}/temp_urls.txt')
		os.system(f'rm {output_path} && mv {results_dir}/temp_urls.txt {output_path}')

	# Store all the endpoints and run httpx
	domain_obj = None
	if domain:
		domain_obj = domain
	elif subdomain:
		domain_obj = subdomain.target_domain

	try:
		endpoint_final_url = output_path
		if not os.path.isfile(endpoint_final_url):
			return

		with open(endpoint_final_url) as endpoint_list:
			for url in endpoint_list:
				http_url = url.rstrip('\n')
				endpoint_query = EndPoint.objects.filter(scan_history=scan_history, http_url=http_url)
				if not endpoint_query.exists():
					_subdomain = get_subdomain_from_url(http_url)
					subdomain_query = Subdomain.objects.filter(
						scan_history=scan_history,
						name=_subdomain
					)
					if subdomain_query.exists():
						subdomain = subdomain_query.first()
					else:
						# gau or gosppider can gather interesting endpoints which
						# when parsed can give subdomains that were not existent from
						# subdomain scan.
						logger.error(
							f'Subdomain {_subdomain} not found, adding...')
						subdomain_dict = DottedDict({
							'scan_history': scan_history,
							'target_domain': domain_obj,
							'name': _subdomain,
						})
						subdomain = save_subdomain(subdomain_dict)
					endpoint_dict = DottedDict({
						'scan_history': scan_history,
						'target_domain': domain_obj,
						'subdomain': subdomain,
						'http_url': http_url,
						'subscan': subscan
					})
					save_endpoint(endpoint_dict)
	except Exception as e:
		logger.error(e)
		if not subscan:
			update_last_activity(activity_id, 0)
		raise Exception(e)

	if send_output_file:
		send_files_to_discord(output_path)

	# TODO:
	# Go spider & waybackurls accumulates a lot of urls, which is good but nuclei
	# takes forever to scan even a simple website, so we will do http probing
	# and filter HTTP status 404, this way we can reduce the number of Non Existent
	# URLS

	# Build CMD
	logger.info('Running httpx probing on collected endpoints ...')
	cmd = f'/go/bin/httpx -l {output_path} -status-code -content-length -ip -cdn -title -tech-detect -json -follow-redirects -random-agent -o {results_dir}/final_httpx_urls.json'
	cmd += f' --http-proxy {proxy}' if proxy else ''
	cmd += f' -H "{custom_header}"' if custom_header else ''
	cmd = remove_cmd_injection_chars(cmd)
	logger.info(cmd)
	os.system(cmd)
	url_results_file = f'{results_dir}/final_httpx_urls.json'
	try:
		if not os.path.isfile(url_results_file):
			logger.error(f'Could not open URL results file {url_results_file}')
			return

		with open(url_results_file, 'r') as f:
			lines = f.readlines()

		for line in lines:
			json_st = json.loads(line.strip())
			http_url = json_st['url']
			subdomain = get_subdomain_from_url(http_url)
			subdomain_query = Subdomain.objects.filter(scan_history=scan_history).filter(name=subdomain)
			if subdomain_query.exists():
				subdomain_obj = subdomain_query.first()
			else:
				subdomain_dict = DottedDict({
					'scan_history': scan_history,
					'target_domain': domain,
					'name': subdomain,
				})
				subdomain_obj = save_subdomain(subdomain_dict)

			# Add Endpoint object to DB
			endpoint = None
			endpoint_query = EndPoint.objects.filter(scan_history=scan_history).filter(http_url=http_url)
			if endpoint_query.exists():
				endpoint = endpoint_query.first()
			else:
				endpoint = EndPoint()
				endpoint_dict = DottedDict({
					'scan_history': scan_history,
					'target_domain': domain,
					'http_url': http_url,
					'subdomain': subdomain_obj
				})
				endpoint = save_endpoint(endpoint_dict)
			endpoint.page_title = json_st.get('title')
			endpoint.webserver = json_st.get('webserver')
			endpoint.content_length = json_st.get('content-length')
			endpoint.http_status = json_st.get('status-code')
			endpoint.webserver = json_st.get('webserver')
			endpoint.save()

			response_time = float(''.join(ch for ch in json_st.get('response-time', '0') if not ch.isalpha()))
			if response_time > 0:
				if json_st['response-time'][-2:] == 'ms':
					response_time = response_time / 1000
				endpoint.response_time = response_time
				endpoint.save()

			technologies = json_st.get('technologies', [])
			for tech_name in technologies:
				if Technology.objects.filter(name=tech_name).exists():
					tech = Technology.objects.get(name=tech_name)
				else:
					tech = Technology(name=tech_name)
					tech.save()
				endpoint.technologies.add(tech)
				subdomain = Subdomain.objects.get(scan_history=scan_history, name=_subdomain)
				subdomain.technologies.add(tech)
				subdomain.save()
				endpoint.save()

	except Exception as e:
		logger.exception(e)
		if not subscan:
			update_last_activity(activity_id, 0)
		raise Exception(e)

	# Send status notif
	if notification and notification.send_scan_status_notif:
		endpoint_count = EndPoint.objects.filter(scan_history__id=scan_history.id).values('http_url').distinct().count()
		endpoint_alive_count = EndPoint.objects.filter(
			scan_history__id=scan_history.id,
			http_status__exact=200).values('http_url').distinct().count()
		msg = f"""reNgine has finished gathering endpoints for {domain_name} and has discovered *{endpoint_count}* unique endpoints.

		*{endpoint_alive_count}/{endpoint_count}* reported HTTP status 200.
		"""
		send_notification(msg)

	# Run gf patterns on saved endpoints
	# TODO: add threading
	gf_patterns = config.get(GF_PATTERNS, [])
	for gf_pattern in gf_patterns:
		# TODO: js var is causing issues, removing for now
		if gf_pattern == 'jsvar':
			logger.warning('Ignoring jsvar as it is causing issues.')
			continue
		logger.info(f'Running GF for {gf_pattern}')
		gf_output_file_path = f'{results_dir}/gf_patterns_{gf_pattern}.txt'
		gf_command = f'cat {output_path} | gf {gf_pattern} | grep -Eo {domain_regex} >> {gf_output_file_path} '
		logger.info(gf_command)
		os.system(gf_command)
		if not os.path.exists(gf_output_file_path):
			logger.error(f'Could not find GF output file {gf_output_file_path}')
			return

		# Read output file line by line and add endpoints / subdomains to DB
		with open(gf_output_file_path) as gf_output:
			lines = gf_output.readlines()
			for url in gf_output:
				try:
					endpoint = EndPoint.objects.get(
						scan_history=scan_history, http_url=url)
					earlier_pattern = endpoint.matched_gf_patterns
					pattern = f'{earlier_pattern},{pattern}' if earlier_pattern else gf_pattern
					endpoint.matched_gf_patterns = pattern
				except Exception as e:
					logger.exception(e)
					logger.info(f'Adding URL {url}')
					endpoint = EndPoint(
						http_url=url,
						target_domain=domain,
						scan_history=scan_history)
					_subdomain = get_subdomain_from_url(url)
					subdomain = Subdomain.objects.get(scan_history=scan_history, name=_subdomain)
					endpoint.subdomain = subdomain
					endpoint.matched_gf_patterns = pattern
				finally:
					endpoint.save()
		os.system(f'rm -rf {gf_output_file_path}')

def vulnerability_scan(
		scan_history,
		activity_id,
		yaml_configuration,
		results_dir,
		domain=None,
		subdomain=None,
		filename='vulns.json',
		subscan=None
	):
	'''
	This function will run nuclei as a vulnerability scanner
	----
	unfurl the urls to keep only domain and path, this will be sent to vuln scan
	ignore certain file extensions
	Thanks: https://github.com/six2dez/reconftw
	'''
	logger.info('Starting vulnerability scan ...')
	cmd = 'nuclei -json'

	# Config
	alive_domains_path = f'{results_dir}/alive.txt'
	config = yaml_configuration[VULNERABILITY_SCAN]
	concurrency = config.get(NUCLEI_CONCURRENCY, 0)
	custom_header = yaml_configuration.get(CUSTOM_HEADER)
	custom_nuclei_template = config.get(NUCLEI_CUSTOM_TEMPLATE, None)
	domain = Domain.objects.get(id=scan_history.domain.id)
	nuclei_template = config.get(NUCLEI_TEMPLATE, None)
	proxy = get_random_proxy()
	rate_limit = config.get(RATE_LIMIT, 0)
	retries = config.get(RETRIES, 0)
	severities = config.get(NUCLEI_SEVERITY, NUCLEI_DEFAULT_SEVERITIES)
	severities_str = ','.join(severities)
	timeout = config.get(TIMEOUT, 0)
	use_nuclei_conf = config.get(USE_NUCLEI_CONFIG, False)
	output_path = f'{results_dir}/{filename}'

	# Find URL
	url = ''
	if subdomain:
		url = subdomain.http_url if subdomain.http_url else f'https://{subdomain.name}'

	# Send start notification
	notification = Notification.objects.first()
	send_vuln = notification.send_vuln_notif if notification else False
	send_status = notification.send_scan_status_notif if notification else False
	if send_status:
		if domain:
			send_notification(f'Vulnerability scan has been initiated for {domain.name}.')
		elif subdomain:
			send_notification(f'Vulnerability scan has been initiated for {subdomain.name}.')

	# Build templates
	logger.info('Updating Nuclei templates ...')
	os.system('nuclei -update-templates')

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
	cmd += ' -debug' if DEBUG > 0 else ''
	cmd += f' -H "{custom_header}"' if custom_header else ''
	cmd += f' -l {alive_domains_path}' if domain else f' -u {url}'
	cmd += f' -c {str(concurrency)}' if concurrency > 0 else ''
	cmd += f' -proxy {proxy} ' if proxy else ''
	cmd += f' -retries {retries}' if retries > 0 else ''
	cmd += f' -rl {str(rate_limit)}' if rate_limit > 0 else ''
	cmd += f' -severity {severities_str}'
	cmd += f' -timeout {str(timeout)}' if timeout > 0 else ''
	for tpl in templates:
		cmd += f' -t {tpl}'

	# Run cmd
	logger.info('Running Nuclei scanner ...')
	logger.info(cmd)
	results = []
	for line in execute_live(cmd):
		if not isinstance(line, dict):
			continue

		try:
			host = line['host']
			subdomain_str = get_subdomain_from_url(host)
			subdomain = Subdomain.objects.get(name=subdomain_str, scan_history=scan_history)
			vulnerability = Vulnerability(
				name=line['info'].get('name', ''),
				type=line['type'],
				subdomain=subdomain,
				scan_history=scan_history,
				target_domain=domain,
				template=line['template'],
				template_url=line['template-url'],
				template_id=line['template-id'],
				severity=NUCLEI_SEVERITY_MAP[line['info'].get('severity', 'unknown')],
				description=line['info'].get('description' ,''),
				matcher_name=line.get('matcher-name', ''),
				http_url=line.get('matched-at'),
				curl_command=line.get('curl-command'),
				extracted_results=line.get('extracted-results', []),
				cvss_metrics=line['info'].get('classification', {}).get('cvss-metrics', ''),
				cvss_score=line['info'].get('classification', {}).get('cvss-score'),
				discovered_date=timezone.now(),
				open_status=True
			)
			vulnerability.save()

			# Get matching endpoint from DB
			endpoint = None
			endpoint_query_all = EndPoint.objects.filter(scan_history=scan_history).filter(target_domain=domain)

			# Create endpoint from host
			endpoint_query = endpoint_query_all.filter(http_url=host)
			if endpoint_query.exists():
				endpoint = endpoint_query.first()
			else:
				endpoint_dict = DottedDict({
					'scan_history': scan_history,
					'target_domain': domain,
					'http_url': host,
					'subdomain': subdomain
				})
				endpoint = save_endpoint(endpoint_dict)
				logger.info(f'EndPoint "{host}" created !')
			vulnerability.endpoint = endpoint

			# Create endpoint from vulnerability http_url
			endpoint_query = endpoint_query_all.filter(http_url=vulnerability.http_url)
			if not endpoint_query.exists():
				endpoint_dict = DottedDict({
					'scan_history': scan_history,
					'target_domain': domain,
					'http_url': vulnerability.http_url,
					'subdomain': subdomain
				})
				save_endpoint(endpoint_dict)
				logger.info(f'Endpoint {vulnerability.http_url} created !')

			# Save tags
			tags = line['info'].get('tags') or []
			for tag in tags:
				vulntags_query = VulnerabilityTags.objects.filter(name=tag)
				if vulntags_query.exists():
					tag = vulntags_query.first()
				else:
					tag = VulnerabilityTags(name=tag)
					tag.save()
				vulnerability.tags.add(tag)
				vulnerability.save()

			# Save CVEs
			cve_ids = line['info'].get('classification', {}).get('cve-id') or []
			for cve in cve_ids:
				cve_query = CveId.objects.filter(name=cve)
				if cve_query.exists():
					cve_obj = cve_query.first()
				else:
					cve_obj = CveId(name=cve)
					cve_obj.save()
				vulnerability.cve_ids.add(cve_obj)
				vulnerability.save()

			# Save CWEs
			cwe_ids = line['info'].get('classification', {}).get('cwe-id') or []
			for cwe in cwe_ids:
				cwe_query = CweId.objects.filter(name=cwe)
				if cwe_query.exists():
					cwe_obj = cwe_query.first()
				else:
					cwe_obj = CweId(name=cwe)
					cwe_obj.save()
				vulnerability.cwe_ids.add(cwe_obj)
				vulnerability.save()

			# Save vuln reference
			references = line['info'].get('reference') or []
			for ref_url in references:
				vulnref_query = VulnerabilityReference.objects.filter(url=ref_url)
				if vulnref_query.exists():
					reference = vulnref_query.first()
				else:
					reference = VulnerabilityReference(url=ref_url)
					reference.save()
				vulnerability.references.add(reference)
				vulnerability.save()

			# Save subscan id in vulnerability object
			if subscan:
				vulnerability.vuln_subscan_ids.add(subscan)
				vulnerability.save()

			# Save vulnerability object
			vulnerability.save()

			# Send notification for all vulnerabilities except info
			url = vulnerability.http_url or vulnerability.subdomain
			logger.info(f'Found vulnerability "{vulnerability.name}" in {url}')				
			if send_vuln:	
				severity_str = line['info'].get('severity', 'info')
				message = f""""*Alert: Vulnerability identified*"

				A *{severity_str.upper()}* severity vulnerability has been identified.'

				Vulnerability Name: {vulnerability.name}'
				Vulnerable URL: {vulnerability.host}'
				"""
				send_notification(message)

			# Send report to hackerone
			hackerone_query = Hackerone.objects.all()
			if hackerone_query.exists() and severity_str not in ('info', 'low') and vulnerability.target_domain.h1_team_handle:
				hackerone = hackerone_query.first()
				if hackerone.send_critical and severity_str == 'critical':
					send_hackerone_report(vulnerability.id)
				elif hackerone.send_high and severity_str == 'high':
					send_hackerone_report(vulnerability.id)
				elif hackerone.send_medium and severity_str == 'medium':
					send_hackerone_report(vulnerability.id)

		except Exception as exception:
			logger.exception(exception)
			if not subscan:
				update_last_activity(activity_id, 0)
			raise Exception(exception)

	# Write results to JSON file
	with open(output_path, 'w') as f:
		json.dump(results, f)

	# Send finish notif
	if send_status:
		vulns_query = Vulnerability.objects.filter(scan_history__id=scan_history.id)
		info_count = vulns_query.filter(severity=0).count()
		low_count = vulns_query.filter(severity=1).count()
		medium_count = vulns_query.filter(severity=2).count()
		high_count = vulns_query.filter(severity=3).count()
		critical_count = vulns_query.filter(severity=4).count()
		unknown_count = vulns_query.filter(severity=-1).count()
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


def scan_failed(scan_history):
	scan_history.scan_status = 0
	scan_history.stop_scan_date = timezone.now()
	scan_history.save()


def create_scan_activity(scan_history, message, status):
	scan_activity = ScanActivity()
	scan_activity.scan_of = scan_history
	scan_activity.title = message
	scan_activity.time = timezone.now()
	scan_activity.status = status
	scan_activity.save()
	return scan_activity.id


def update_last_activity(id, activity_status, error_message=None):
	ScanActivity.objects.filter(id=id).update(
		status=activity_status,
		error_message=error_message,
		time=timezone.now())


def save_subdomain(subdomain):
	subdomain = Subdomain(
		discovered_date=timezone.now(),
		target_domain=subdomain.get('target_domain'),
		scan_history=subdomain.get('scan_history'),
		name=subdomain.get('name'),
		http_url=subdomain.get('http_url'),
		screenshot_path=subdomain.get('screenshot_path'),
		http_header_path=subdomain.get('http_header_path'),
		cname=subdomain.get('cname'),
		is_cdn=subdomain.get('is_cdn'),
		content_type=subdomain.get('content_type'),
		webserver=subdomain.get('webserver'),
		page_title=subdomain.get('page_title'),
		is_imported_subdomain=subdomain.get('is_imported_subdomain', False),
		http_status=subdomain.get('http_status', 0),
		response_time=subdomain.get('response_time'),
		content_length=subdomain.get('content_length')
	)
	subdomain.save()
	return subdomain


def save_endpoint(endpoint_dict):
	endpoint = EndPoint(
		discovered_date=timezone.now(),
		scan_history=endpoint_dict.get('scan_history'),
		target_domain=endpoint_dict.get('target_domain'),
		subdomain=endpoint_dict.get('subdomain'),
		http_url=endpoint_dict.get('http_url'),
		page_title=endpoint_dict.get('page_title'),
		content_type=endpoint_dict.get('content_type'),
		webserver=endpoint_dict.get('webserver'),
		response_time=endpoint_dict.get('response_time', 0),
		http_status=endpoint_dict.get('http_status', 0),
		content_length=endpoint_dict.get('content_length', 0),
		is_default=endpoint_dict.get('is_default', False)
	)
	endpoint.save()
	subscan = endpoint_dict.get('subscan')
	if subscan:
		endpoint.endpoint_subscan_ids.add(subscan)
		endpoint.save()
	return endpoint


def perform_osint(scan_history, domain, yaml_configuration, results_dir):
	notification = Notification.objects.first()
	send_status = notification.send_scan_status_notif if notification else False
	logger.info(f'Performing OSInt on {domain} ...')
	if send_status:
		send_notification(f'reNgine has initiated OSINT on target {domain.name}')

	if 'discover' in yaml_configuration[OSINT]:
		osint_discovery(scan_history, domain, yaml_configuration, results_dir)

	if 'dork' in yaml_configuration[OSINT]:
		dorking(scan_history, yaml_configuration)

	if send_status:
		send_notification(f'reNgine has completed performing OSINT on target {domain.name}')


def osint_discovery(scan_history, domain, yaml_configuration, results_dir):
	osint_config = yaml_configuration[OSINT]
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
	dorks = yaml_configuration[OSINT].get(OSINT_DORK, DORKS_DEFAULT_NAMES)
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
		dork, _ = Dork.objects.get_or_create(
			type=type,
			description=result['desc'],
			url=result['url']
		)
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
	logger.info(f'Running theHarvester on {scan_history.domain.name} ...')
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
	logger.info('Parsing theHarvester results ...')
	with open(output_filepath, 'r') as f:
		data = json.load(f)

	emails = data.get('emails', [])
	hosts = data.get('hosts', [])
	ips = data.get('ips', [])
	linkedin_people = data.get('linkedin_people', [])
	twitter_people = data.get('twitter_people', [])

	for email_address in emails:
		logger.info(f'Found email address {email_address}')
		email, _ = Email.objects.get_or_create(address=email_address)
		scan_history.emails.add(email)
		scan_history.save()

	for people in linkedin_people:
		logger.info(f'Found employee {people}')
		employee, _ = Employee.objects.get_or_create(name=people, designation='linkedin')
		scan_history.employees.add(employee)
		scan_history.save()

	for people in twitter_people:
		logger.info(f'Found employee {people}')
		employee, _ = Employee.objects.get_or_create(name=people, designation='twitter')
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
	logger.info('OSINT: Getting leaked credentials...')
	leak_target_path = f'{results_dir}/creds_target.txt'
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
			logger.error('Could not read JSON output from pwndb output.')
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
	logger.info(f'Getting metadata for {meta_dict.osint_target}')

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
		subdomain = Subdomain.objects.get(scan_history=meta_dict.scan_id, name=meta_dict.osint_target)
		metadata = DottedDict(metadata)
		logger.info(metadata)
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

@app.task
def query_whois(ip_domain, save_db=False, fetch_from_db=True):
	print(f'Running whois on {ip_domain}. Fetch from db ? {fetch_from_db}; Save to db ? {save_db}')
	domain_query = Domain.objects.filter(name=ip_domain)
	if fetch_from_db:
		if not domain_query.exists():
			return {
				'status': False,
				'message': f'Domain {ip_domain} does not exist as a Domain in the Database.'
			}
		domain_info = domain_query.first().domain_info
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
	else:
		result = asyncwhois.whois_domain(ip_domain)
		whois = result.parser_output
		if not whois.get('domain_name'):
			return {
				'status': False,
				'ip_domain': ip_domain,
				'result': 'Unable to fetch records from WHOIS database.'
			}
		created = whois.get('created')
		expires = whois.get('expires')
		updated = whois.get('updated')
		dnssec = whois.get('dnssec')

		# Save whois information in various tables
		if save_db and domain_query.exists():
			domain = domain_query.first()
			logger.info(f'Saving domain "{domain}" info in DB!')
			domain_info = DomainInfo(
				raw_text=result.query_output.strip(),
				dnssec=dnssec,
				created=created,
				updated=updated,
				expires=expires)
			
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
			data = {}
			logger.info(f'Gathering domain details for {ip_domain}...')
			for field_parent, fields in whois_fields.items():
				data[field_parent] = {}
				for (field_name, model_cls) in fields:
					field_fullname = f'{field_parent}_{field_name}' if field_parent != 'default' else field_name
					field_content = whois.get(field_fullname)
					serializer_cls = globals()[model_cls.__name__ + 'Serializer']

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
						continue
					obj_json = serializer_cls(obj, many=False).data
					logger.info(obj_json)
					data[field_parent][field_name] = obj_json['name']

					# Set attribute in domain_info
					logger.info(f'Setting {field_fullname} in DomainInfo object ...')
					setattr(domain_info, field_fullname, obj)
					domain_info.save()

			logger.info(f'Finished saving domain info {ip_domain}.')

			# Whois status
			whois_status = whois.get('status', [])
			for _status in whois_status:
				domain_whois, _ = DomainWhoisStatus.objects.get_or_create(status=_status)
				domain_info.status.add(domain_whois)
				domain_whois_json = DomainWhoisStatusSerializer(domain_whois, many=False).data
				if 'whois_status' in data:
					data['whois_status'].append(domain_whois_json)
				else:
					data['whois_status'] = [domain_whois_json]

			# Nameservers
			nameservers = whois.get('name_servers', [])
			for name_server in nameservers:
				ns, _ = NameServers.objects.get_or_create(name=name_server)
				domain_info.name_servers.add(ns)
				ns_json = NameServersSerializer(ns, many=False).data
				if 'name_servers' in data:
					data['name_servers'].append(ns_json)
				else:
					data['name_servers'] = [ns_json]

			# Save domain in DB
			domain.domain_info = domain_info
			domain.save()

			import pprint
			logger.info(pprint.pformat(data))

			return {
				'status': True,
				'ip_domain': ip_domain,
				'domain': {
					'created': created,
					'updated': updated,
					'expires': expires,
					'registrar': domain_info.registrar,
					'geolocation_iso': data['registrant']['country'],
					'dnssec': dnssec,
					'status': _status,
				},
				'registrant': data['registrant'],
				'admin': data['admin'],
				'technical_contact': data['tech'],
				'nameservers': data['name_servers'],
				'raw_text': result.query_output.strip()
			}

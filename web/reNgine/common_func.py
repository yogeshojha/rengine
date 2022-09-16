from cgitb import lookup
import json
import logging
import os
import random
import shutil
from datetime import date
from threading import Thread
from urllib.parse import urlparse

import requests
import tldextract
from discord_webhook import DiscordWebhook
from django.db.models import Q
from reNgine.common_serializers import *
from reNgine.definitions import *
from scanEngine.models import *
from startScan.models import *
from targetApp.models import *

logger = logging.getLogger(__name__)

#------------------#
# EngineType utils #
#------------------#
def dump_custom_scan_engines(results_dir):
	"""Dump custom scan engines to YAML files.
	
	Args:
		results_dir (str): Results directory (will be created if non-existent).
	"""
	custom_engines = EngineType.objects.filter(default_engine=False)
	if not os.path.exists(results_dir):
		os.makedirs(results_dir, exist_ok=True)
	for engine in custom_engines:
		with open(f'{results_dir}/{engine.engine_name}.yaml', 'w') as f:
			config = yaml.safe_load(engine.yaml_configuration)
			yaml.dump(config, f, indent=4)

def load_custom_scan_engines(results_dir):
	"""Load custom scan engines from YAML files. The filename without .yaml will 
	be used as the engine name.
	
	Args:
		results_dir (str): Results directory containing engines configs.
	"""
	config_paths = [
		f for f in os.listdir(results_dir)
		if os.path.isfile(os.path.join(results_dir, f))
	]
	for path in config_paths:
		engine_name = path.replace('.yaml', '').split('/')[-1]
		full_path = os.path.join(results_dir, path)
		with open(full_path, 'r') as f:
			yaml_configuration = yaml.safe_load(f)
		engine, _ = EngineType.objects.get_or_create(engine_name=engine_name)
		engine.yaml_configuration = yaml.dump(yaml_configuration)
		engine.save()


#------------------#
# Database queries #
#------------------#
def get_lookup_keywords():
	"""Get lookup keywords from InterestingLookupModel.
	
	Returns:
		list: Lookup keywords.
	"""
	lookup_model = InterestingLookupModel.objects.first()
	lookup_obj = InterestingLookupModel.objects.filter(custom_type=True).order_by('-id').first()
	custom_lookup_keywords = []
	default_lookup_keywords = []
	if lookup_model:
		default_lookup_keywords = [
			key.strip()
			for key in lookup_model.keywords.split(',')]
	if lookup_obj:
		custom_lookup_keywords = [
			key.strip()
			for key in lookup_obj.keywords.split(',')
		]
	lookup_keywords = default_lookup_keywords + custom_lookup_keywords
	lookup_keywords = list(filter(None, lookup_keywords)) # remove empty strings from list
	return lookup_keywords


def get_interesting_subdomains(scan_history=None, target=None):
	"""Get Subdomain objects matching InterestingLookupModel conditions.

	Args:
		scan_history (startScan.models.ScanHistory): Scan history.
		target (str): Domain id.

	Returns:
		django.db.Q: QuerySet object.
	"""
	lookup_keywords = get_lookup_keywords()
	lookup_obj = InterestingLookupModel.objects.filter(custom_type=True).order_by('-id').first()
	url_lookup = lookup_obj.url_lookup
	title_lookup = lookup_obj.title_lookup
	condition_200_http_lookup = lookup_obj.condition_200_http_lookup
	if not lookup_obj:
		return Subdomain.objects.none()

	# Filter on domain_id, scan_history_id
	query = Subdomain.objects
	if target:
		query = query.filter(target_domain__id=target)
	elif scan_history:
		query = query.filter(scan_history__id=scan_history)

	# Filter on HTTP status code 200
	if condition_200_http_lookup:
		query = query.filter(http_status__exact=200)

	# Build subdomain lookup / page title lookup queries
	url_lookup_query = Q()
	title_lookup_query = Q()
	for key in lookup_keywords:
		if url_lookup:
			url_lookup_query |= Q(name__icontains=key)
		if title_lookup:
			title_lookup_query |= Q(page_title__iregex=f"\\y{key}\\y")

	# Filter on url / title queries
	url_lookup_query = query.filter(url_lookup_query)
	title_lookup_query = query.filter(title_lookup_query)

	# Return OR query
	return url_lookup_query | title_lookup_query


def get_interesting_endpoints(scan_history=None, target=None):
	"""Get EndPoint objects matching InterestingLookupModel conditions.

	Args:
		scan_history (startScan.models.ScanHistory): Scan history.
		target (str): Domain id.

	Returns:
		django.db.Q: QuerySet object.
	"""

	lookup_keywords = get_lookup_keywords()
	lookup_obj = InterestingLookupModel.objects.filter(custom_type=True).order_by('-id').first()
	url_lookup = lookup_obj.url_lookup
	title_lookup = lookup_obj.title_lookup
	condition_200_http_lookup = lookup_obj.condition_200_http_lookup
	if not lookup_obj:
		return EndPoint.objects.none()

	# Filter on domain_id, scan_history_id
	query = EndPoint.objects
	if target:
		query = query.filter(target_domain__id=target)
	elif scan_history:
		query = query.filter(scan_history__id=scan_history)

	# Filter on HTTP status code 200
	if condition_200_http_lookup:
		query = query.filter(http_status__exact=200)

	# Build subdomain lookup / page title lookup queries
	url_lookup_query = Q()
	title_lookup_query = Q()
	for key in lookup_keywords:
		if url_lookup:
			url_lookup_query |= Q(http_url__icontains=key)
		if title_lookup:
			title_lookup_query |= Q(page_title__iregex=f"\\y{key}\\y")

	# Filter on url / title queries
	url_lookup_query = query.filter(url_lookup_query)
	title_lookup_query = query.filter(title_lookup_query)

	# Return OR query
	return url_lookup_query | title_lookup_query


def get_subdomains(target_domain, scan_history=None, url_path='', subdomain_id=None, exclude_subdomains=None, write_filepath=None):
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

	if url_path:
		subdomains = [f'{subdomain}/{url_path}' for subdomain in subdomains]

	if write_filepath:
		with open(write_filepath, 'w') as f:
			f.write('\n'.join(subdomains))

	return subdomains


def get_http_urls(
		target_domain,
		subdomain_id=None,
		scan_history=None,
		is_alive=False,
		url_path='',
		ignore_files=False,
		exclude_subdomains=False,
		write_filepath=None):
	"""Get HTTP urls from EndPoint objects in DB. Support filtering out on a 
	specific path.

	Args:
		target_domain (startScan.models.Domain): Target Domain object.
		scan_history (startScan.models.ScanHistory, optional): ScanHistory object.
		is_alive (bool): If True, select only alive subdomains.
		path (str): URL path.
		write_filepath (str): Write info back to a file.

	Returns:
		list: List of subdomains matching query.
	"""
	base_query = EndPoint.objects.filter(target_domain=target_domain)
	if scan_history:
		base_query = base_query.filter(scan_history=scan_history)
	if subdomain_id:
		subdomain = Subdomain.objects.get(pk=subdomain_id)
		base_query = base_query.filter(http_url__contains=subdomain.name)
	elif exclude_subdomains:
		base_query = base_query.filter(name=target_domain.name)

	# If a path is passed, select only endpoints that contains it
	if url_path:
		url = f'{target_domain.name}/{url_path}'
		base_query = base_query.filter(http_url__contains=url)

	# Select distinct endpoints and order
	endpoints = base_query.distinct('http_url').order_by('http_url').all()

	# If is_alive is True, select only endpoints that are alive
	if is_alive:
		endpoints = [e for e in endpoints if e.is_alive]

	# Grab only http_url from endpoint objects
	endpoints = [e.http_url for e in endpoints]
	if ignore_files: # ignore all files
		# TODO: not hardcode this
		extensions_path = '/usr/src/app/fixtures/extensions.txt'
		with open(extensions_path, 'r') as f:
			extensions = tuple(f.readlines())
		endpoints = [e for e in endpoints if not urlparse(e).path.endswith(extensions)]

	if not endpoints:
		logger.error(f'No endpoints were found in query for {target_domain.name}!')

	if write_filepath:
		with open(write_filepath, 'w') as f:
			f.write('\n'.join(endpoints))

	return endpoints


def get_subdomain_from_url(url):
	"""Get subdomain from HTTP URL.
	
	Args:
		url (str): HTTP URL.

	Returns:
		str: Subdomain name.
	"""
	url_obj = urlparse(url.strip())
	url_str = url_obj.netloc if url_obj.scheme else url_obj.path
	return url_str.split(':')[0]


def get_domain_from_subdomain(subdomain):
	"""Get domain from subdomain.
	
	Args:
		subdomain (str): Subdomain name.

	Returns:
		str: Domain name.
	"""
	ext = tldextract.extract(subdomain)
	return '.'.join(ext[1:3])


def get_random_proxy():
	"""Get a random proxy from the list of proxies input by user in the UI.
	
	Returns:
		str: Proxy name or '' if no proxy defined in db or use_proxy is False.
	"""
	if not Proxy.objects.all().exists():
		return ''
	proxy = Proxy.objects.first()
	if not proxy.use_proxy:
		return ''
	proxy_name = random.choice(proxy.proxies.splitlines())
	logger.warning('Using proxy: ' + proxy_name)
	# os.environ['HTTP_PROXY'] = proxy_name
	# os.environ['HTTPS_PROXY'] = proxy_name
	return proxy_name


def send_hackerone_report(vulnerability_id):
	"""Send hackerone report.
	
	Args:
		vulnerability_id (int): Vulnerability id.

	Returns:
		int: HTTP response status code.
	"""
	vulnerability = Vulnerability.objects.get(id=vulnerability_id)
	severities = {v: k for k,v in NUCLEI_SEVERITY_MAP.items()}
	headers = {
		'Content-Type': 'application/json',
		'Accept': 'application/json'
	}

	# can only send vulnerability report if team_handle exists
	if len(vulnerability.target_domain.h1_team_handle) !=0:
		hackerone_query = Hackerone.objects.all()
		if hackerone_query.exists():
			hackerone = Hackerone.objects.first()
			severity_value = severities[vulnerability.severity]
			tpl = hackerone.report_template

			# Replace syntax of report template with actual content
			tpl = tpl.replace('{vulnerability_name}', vulnerability.name)
			tpl = tpl.replace('{vulnerable_url}', vulnerability.http_url)
			tpl = tpl.replace('{vulnerability_severity}', severity_value)
			tpl = tpl.replace('{vulnerability_description}', vulnerability.description if vulnerability.description else '')
			tpl = tpl.replace('{vulnerability_extracted_results}', vulnerability.extracted_results if vulnerability.extracted_results else '')
			tpl = tpl.replace('{vulnerability_reference}', vulnerability.reference if vulnerability.reference else '')

			data = {
			  "data": {
				"type": "report",
				"attributes": {
				  "team_handle": vulnerability.target_domain.h1_team_handle,
				  "title": '{} found in {}'.format(vulnerability.name, vulnerability.http_url),
				  "vulnerability_information": tpl,
				  "severity_rating": severity_value,
				  "impact": "More information about the impact and vulnerability can be found here: \n" + vulnerability.reference if vulnerability.reference else "NA",
				}
			  }
			}

			r = requests.post(
			  'https://api.hackerone.com/v1/hackers/reports',
			  auth=(hackerone.username, hackerone.api_key),
			  json=data,
			  headers=headers
			)
			response = r.json()
			status_code = r.status_code
			if status_code == 201:
				vulnerability.hackerone_report_id = response['data']["id"]
				vulnerability.open_status = False
				vulnerability.save()
			return status_code

	else:
		logger.error('No team handle found.')
		status_code = 111
		return status_code


def get_cms_details(url):
	"""Get CMS details using cmseek.py.
	
	Args:
		url (str): HTTP URL.

	Returns:
		dict: Response.
	"""
	# this function will fetch cms details using cms_detector
	response = {}
	cms_detector_command = f'python3 /usr/src/github/CMSeeK/cmseek.py --random-agent --batch --follow-redirect -u {url}'
	os.system(cms_detector_command)

	response['status'] = False
	response['message'] = 'Could not detect CMS!'

	parsed_url = urlparse(url)

	domain_name = parsed_url.hostname
	port = parsed_url.port

	find_dir = domain_name

	if port:
		find_dir += '_{}'.format(port)

	# subdomain may also have port number, and is stored in dir as _port

	cms_dir_path =  '/usr/src/github/CMSeeK/Result/{}'.format(find_dir)
	cms_json_path =  cms_dir_path + '/cms.json'

	if os.path.isfile(cms_json_path):
		cms_file_content = json.loads(open(cms_json_path, 'r').read())
		if not cms_file_content.get('cms_id'):
			return response
		response = {}
		response = cms_file_content
		response['status'] = True
		# remove cms dir path
		try:
			shutil.rmtree(cms_dir_path)
		except Exception as e:
			print(e)

	return response

def sanitize_url(http_url):
	"""Removes HTTP ports 80 and 443 from HTTP URL because it's ugly.

	Args:
		http_url (str): Input HTTP URL.

	Returns:
		str: Stripped HTTP URL.
	"""
	url = urlparse(http_url)
	if url.netloc.endswith(':80'):
		url = url._replace(netloc=url.netloc.replace(':80', ''))
	elif url.netloc.endswith(':443'):
		url = url._replace(netloc=url.netloc.replace(':443', ''))
	return url.geturl().rstrip('/')


def format_notification_message(message, scan_history_id, subscan_id):
	"""Add scan id / subscan id to notification message.
	
	Args:
		message (str): Original notification message.
		scan_history_id (int): Scan history id.
		subscan_id (int): Subscan id.
	
	Returns:
		str: Message.
	"""
	if scan_history_id is not None:
		if subscan_id:
			message = f'`#{scan_history_id}_{subscan_id}`: {message}'
		else:
			message = f'`#{scan_history_id}`: {message}'
	return message
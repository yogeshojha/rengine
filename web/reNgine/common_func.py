import json
import logging
import os
import pickle
import random
import shutil
import traceback
from ftplib import FTP
from http.client import HTTPConnection, HTTPSConnection
from time import sleep
from urllib.parse import urlparse

import humanize
import redis
import requests
import tldextract
import xmltodict
from discord_webhook import DiscordEmbed, DiscordWebhook
from django.db.models import Q
from dotted_dict import DottedDict
from reNgine.common_serializers import *
from reNgine.definitions import *
from reNgine.settings import *
from scanEngine.models import *
from startScan.models import *
from targetApp.models import *

logger = logging.getLogger(__name__)
DISCORD_WEBHOOKS_CACHE = redis.Redis.from_url(CELERY_BROKER_URL)

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


#--------------------------------#
# InterestingLookupModel queries #
#--------------------------------#
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


#-------------------#
# SubDomain queries #
#-------------------#

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

def get_new_added_subdomain(scan_id, domain_id):
	"""Find domains added during the last scan.

	Args:
		scan_id (int): startScan.models.ScanHistory ID.
		domain_id (int): startScan.models.Domain ID.

	Returns:
		django.models.querysets.QuerySet: query of newly added subdomains.
	"""
	scan = (
		ScanHistory.objects
		.filter(domain=domain_id)
		.filter(tasks__overlap=['subdomain_discovery'])
		.filter(id__lte=scan_id)
	)
	if not scan.count() > 1:
		return
	last_scan = scan.order_by('-start_scan_date')[1]
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
	"""Find domains removed during the last scan.

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
	removed_subdomains = scanned_host_q2.difference(scanned_host_q1)
	return (
		Subdomain.objects
		.filter(scan_history=last_scan)
		.filter(name__in=removed_subdomains)
	)


def get_interesting_subdomains(scan_history=None, domain_id=None):
	"""Get Subdomain objects matching InterestingLookupModel conditions.

	Args:
		scan_history (startScan.models.ScanHistory, optional): Scan history.
		domain_id (int, optional): Domain id.

	Returns:
		django.db.Q: QuerySet object.
	"""
	lookup_keywords = get_lookup_keywords()
	lookup_obj = (
		InterestingLookupModel.objects
		.filter(custom_type=True)
		.order_by('-id').first())
	if not lookup_obj:
		return Subdomain.objects.none()

	url_lookup = lookup_obj.url_lookup
	title_lookup = lookup_obj.title_lookup
	condition_200_http_lookup = lookup_obj.condition_200_http_lookup

	# Filter on domain_id, scan_history_id
	query = Subdomain.objects
	if domain_id:
		query = query.filter(target_domain__id=domain_id)
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


#------------------#
# EndPoint queries #
#------------------#

def get_http_urls(
		target_domain,
		subdomain_id=None,
		scan_history=None,
		is_alive=False,
		url_path='',
		strict=False,
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
		base_query = base_query.filter(http_url=target_domain.http_url)

	# If a path is passed, select only endpoints that contains it
	if url_path:
		url = f'{target_domain.name}/{url_path}'
		url = url.rstrip('/')
		if strict:
			base_query = base_query.filter(http_url=url)
		else:
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
	if not lookup_obj:
		return EndPoint.objects.none()
	url_lookup = lookup_obj.url_lookup
	title_lookup = lookup_obj.title_lookup
	condition_200_http_lookup = lookup_obj.condition_200_http_lookup

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


#-----------#
# URL utils #
#-----------#

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


def probe_url(url, method='HEAD', first=False):
	"""Probe URL to find out which protocols respond for this URL.

	Args:
		url (str): URL.
		method (str): HTTP method to probe with. Default: HEAD.
		first (bool): Return only first successful probe URL.

	Returns:
		list: List of URLs that responded.
		str: First URL that responded.
	"""
	http_alive, http_url, http_resp = is_alive(url, scheme='http', method=method)
	https_alive, https_url, https_resp = is_alive(url, scheme='https', method=method)
	alive_ftp, ftp_url, _ = is_alive(url, scheme='ftp')
	urls = []
	if http_alive:
		url = getattr(http_resp, 'url', http_url)
		urls.append(url)
	if https_alive:
		url = getattr(https_resp, 'url', https_url)
		urls.append(url)
	if alive_ftp:
		urls.append(ftp_url)
	urls = [sanitize_url(url) for url in urls]
	logger.info(f'Probed "{url}" and found {len(urls)} alive URLs: {urls}')
	if first:
		if urls:
			return urls[0]
		return None
	return urls


def is_alive(url, scheme='https', method='HEAD', timeout=DEFAULT_HTTP_TIMEOUT):
	""""Check if URL is alive on a certain scheme (protocol).

	Args:
		url (str): URL with or without protocol.
		protocol (str): Protocol to check. Default: https
		method (str): HTTP method to use.

	Returns:
		tuple: (is_alive [bool], url [str], response [HTTPResponse]).
	"""
	url = urlparse(url)
	if not url.scheme: # no scheme in input URL, adding input scheme to URL
		url = urlparse(f'{scheme}://{url.geturl()}')
	if url.scheme != scheme:
		return False, None, None
	final_url = url.geturl()
	try:
		if scheme == 'https':
			connection = HTTPSConnection(url.netloc, timeout=timeout)
			connection.request(method, url.path)
			resp = connection.getresponse()
			if resp:
				return True, final_url, resp
			return False, None, None
		elif scheme == 'http':
			connection = HTTPConnection(url.netloc, timeout=timeout)
			connection.request(method, url.path)
			resp = connection.getresponse()
			if resp:
				return True, final_url, resp
			return False, None, None
		elif scheme == 'ftp':
			ftp = FTP(url.netloc)
			resp1 = ftp.connect(timeout=timeout)
			resp2 = ftp.voidcmd('NOOP')
			status, msg = tuple(resp2.split(' NOOP command '))
			# TODO: make this look like an HTTPResponse object
			resp = DottedDict({
				'status': int(status),
				'noop_info': resp2,
				'connect_info': resp1
			})
			return True, final_url, resp
		else:
			return False, None, None
	except Exception as e:
		print(str(e))
		return False, None, None


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


#-------#
# Utils #
#-------#

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


#--------------------#
# NOTIFICATION UTILS #
#--------------------#

def send_telegram_message(message):
	"""Send Telegram message.
	
	Args:
		message (str): Message.
	"""
	notif = Notification.objects.first()
	do_send = (
		notif and
		notif.send_to_telegram and
		notif.telegram_bot_token and
		notif.telegram_bot_chat_id)
	if not do_send:
		return
	telegram_bot_token = notif.telegram_bot_token
	telegram_bot_chat_id = notif.telegram_bot_chat_id
	send_url = f'https://api.telegram.org/bot{telegram_bot_token}/sendMessage?chat_id={telegram_bot_chat_id}&parse_mode=Markdown&text={message}'
	requests.get(send_url)


def send_slack_message(message):
	"""Send Slack message.
	
	Args:
		message (str): Message.
	"""
	headers = {'content-type': 'application/json'}
	message = {'text': message}
	notif = Notification.objects.first()
	do_send = (
		notif and 
		notif.send_to_slack and
		notif.slack_hook_url)
	if not do_send:
		return
	hook_url = notif.slack_hook_url
	requests.post(url=hook_url, data=json.dumps(message), headers=headers)


def send_discord_message(
		message,
		title='',
		severity='info',
		url=None,
		files=None,
		fields={},
		fields_append=[]):
	"""Send Discord message.
	
	If title and fields are specified, ignore the 'message' and create a Discord
	embed that can be updated later if specifying the same title (title is the
	cache key).

	Args:
		message (str): Message to send. If an embed is used, this is ignored.
		severity (str, optional): Severity. Colors are picked based on severity.
		files (list, optional): List of files to attach to message.
		title (str, optional): Discord embed title.
		url (str, optional): Discord embed URL.
		fields (dict, optional): Discord embed fields.
		fields_append (list, optional): Discord embed field names to update
			instead of overwrite.
	"""

	# Check if do send
	notif = Notification.objects.first()
	if not (notif and notif.send_to_discord and notif.discord_hook_url):
		return False

	# If fields and title, use an embed
	use_discord_embed = fields and title
	if use_discord_embed:
		message = '' # no need for message in embeds

	# Check for cached response in cache, using title as key
	cached_response = DISCORD_WEBHOOKS_CACHE.get(title) if title else None
	if cached_response:
		cached_response = pickle.loads(cached_response)

	# Get existing webhook if found in cache
	cached_webhook = DISCORD_WEBHOOKS_CACHE.get(title + '_webhook') if title else None
	if cached_webhook:
		webhook = pickle.loads(cached_webhook)
		webhook.remove_embeds()
	else:
		webhook = DiscordWebhook(
			url=notif.discord_hook_url,
			rate_limit_retry=True,
			content=message)

	# Get existing embed if found in cache
	embed = None
	cached_embed = DISCORD_WEBHOOKS_CACHE.get(title + '_embed') if title else None
	if cached_embed:
		embed = pickle.loads(cached_embed) 
	elif use_discord_embed:
		embed = DiscordEmbed(title=title)

	# Set embed fields
	if embed:
		embed.set_url(url)
		embed.set_color(DISCORD_SEVERITY_COLORS[severity])
		embed.set_description(message)
		embed.set_timestamp()
		existing_fields_dict = {field['name']: field['value'] for field in embed.fields}
		for name, value in fields.items():
			if not value: # cannot send empty field values to Discord [error 400]
				continue
			value = str(value)
			new_field = {'name': name, 'value': value, 'inline': False}

			# If field already existed in previous embed, update it.
			if name in existing_fields_dict.keys():
				field = [f for f in embed.fields if f['name'] == name][0]

				# Append to existing field value
				if name in fields_append:
					existing_val = field['value']
					existing_val = str(existing_val)
					if value not in existing_val:
						value = f'{existing_val}\n{value}'

				# Update existing embed
				ix = embed.fields.index(field)
				embed.fields[ix]['value'] = value

			else:
				embed.add_embed_field(**new_field)

		webhook.add_embed(embed)

		# Add webhook and embed objects to cache so we can pick them up later
		DISCORD_WEBHOOKS_CACHE.set(title + '_webhook', pickle.dumps(webhook))
		DISCORD_WEBHOOKS_CACHE.set(title + '_embed', pickle.dumps(embed))

	# Add files to webhook
	if files:
		for (path, name) in files:
			with open(path, 'r') as f:
				content = f.read()
			webhook.add_file(content, name)

	# Edit webhook if it already existed, otherwise send new webhook
	if cached_response:
		response = webhook.edit(cached_response)
	else:
		response = webhook.execute()
		if use_discord_embed and response.status_code == 200:
			DISCORD_WEBHOOKS_CACHE.set(title, pickle.dumps(response))

	# Get status code
	if response.status_code == 429:
		errors = json.loads(response.content.decode('utf-8'))
		wh_sleep = (int(errors['retry_after']) / 1000) + 0.15
		logger.warning(f'Rate limited while sending webhook data to Discord. Retrying in {wh_sleep}.')
		sleep(wh_sleep)
		send_discord_message(
			message,
			title=title,
			severity=severity,
			url=url,
			files=files,
			fields=fields,
			fields_append=fields_append)
	elif response.status_code != 200:
		logger.error(
			f'Error while sending webhook data to Discord.'
			f'\n\tHTTP code: {response.status_code}.'
			f'\n\tDetails: {response.content}')


def enrich_notification(message, scan_history_id, subscan_id):
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


def get_scan_title(scan_id, subscan_id=None, task_name=None):
	return f'Subscan #{subscan_id} summary' if subscan_id else f'Scan #{scan_id} summary'


def get_scan_url(scan_id, subscan_id=None):
	return f'https://{DOMAIN_NAME}/scan/detail/{scan_id}'


def get_scan_fields(engine, scan, subscan=None, status='RUNNING', tasks=[]):
	scan_obj = subscan if subscan else scan
	if subscan:
		tasks_h = f'`{subscan.type}`'
		host = subscan.subdomain.name
		scan_obj = subscan
	else:
		tasks_h = '\n• '.join(f'`{task.name}`' for task in tasks)
		host = scan.domain.name
		scan_obj = scan

	# Find scan elapsed time
	duration = None
	if scan_obj and status in ['ABORTED', 'FAILED', 'SUCCESS']:
		td = scan_obj.stop_scan_date - scan_obj.start_scan_date
		duration = humanize.naturaldelta(td)
	elif scan_obj:
		td = timezone.now() - scan_obj.start_scan_date
		duration = humanize.naturaldelta(td)

	# Build fields
	url = get_scan_url(scan.id)
	fields = {
		'Status': f'**{status}**',
		'Engine': engine.engine_name,
		'Scan ID': f'[#{scan.id}]({url})'
	}

	if subscan:
		url = get_scan_url(scan.id, subscan.id)
		fields['Subscan ID'] = f'[#{subscan.id}]({url})'

	if duration:
		fields['Duration'] = duration

	fields.update({
		'Host': host,
		'Tasks': tasks_h
	})

	return fields


def get_task_title(task_name, scan_id, subscan_id=None):
	if subscan_id:
		return f'`#{scan_id}-#{subscan_id}` - `{task_name}`'
	return f'`#{scan_id}` - `{task_name}`'


def get_task_header_message(name, scan_history_id, subscan_id):
	msg = f'`{name}` [#{scan_history_id}'
	if subscan_id:
		msg += f'_#{subscan_id}]'
	msg += 'status'
	return msg


def get_task_cache_key(func_name, *args, **kwargs):
	args_str = '_'.join([str(arg) for arg in args])
	kwargs_str = '_'.join([f'{k}={v}' for k, v in kwargs.items() if k not in RENGINE_TASK_IGNORE_CACHE_KWARGS])
	return f'{func_name}__{args_str}__{kwargs_str}'


def get_output_file_name(scan_history_id, subscan_id, filename):
	title = f'#{scan_history_id}'
	if subscan_id:
		title += f'-{subscan_id}'
	title += f'_{filename}'
	return title


def get_traceback_path(task_name, results_dir, scan_history_id=None, subscan_id=None):
	path = results_dir
	if scan_history_id:
		path = f'{path}/{task_name}_#{scan_history_id}'
	if subscan_id:
		path += f'-#{subscan_id}'
	path += '.txt'
	return path


def fmt_traceback(exc):
	return '\n'.join(traceback.format_exception(None, exc, exc.__traceback__))


#--------------#
# CLI BUILDERS #
#--------------#

def get_nmap_cmd(
		input_file,
		cmd=None,
		host=None,
		ports=None,
		output_file=None,
		script=None,
		script_args=None,
		max_rate=None,
		service_detection=True,
		flags=[]):
	if not cmd:
		cmd = 'nmap'
	cmd += f' -sV' if service_detection else ''
	cmd += f' -p {ports}' if ports else ''
	for flag in flags:
		cmd += flag
	cmd += f' --script {script}' if script else ''
	cmd += f' --script-args {script_args}' if script_args else ''
	cmd += f' --max-rate {max_rate}' if max_rate else ''
	cmd += f' -oX {output_file}' if output_file else ''
	if input_file:
		cmd += f' -iL {input_file}'
	elif host:
		cmd += f' {host}'
	return cmd

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


def xml2json(xml): 
    xmlfile = open(xml)
    xml_content = xmlfile.read()
    xmlfile.close()
    xmljson = json.dumps(xmltodict.parse(xml_content), indent=4, sort_keys=True)
    jsondata = json.loads(xmljson)
    return jsondata
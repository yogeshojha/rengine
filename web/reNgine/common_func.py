import whatportis
import socket
import json
import os
import pickle
import random
import shutil
import traceback
import ipaddress
import humanize
import redis
import requests
import tldextract
import xmltodict

from time import sleep
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from celery.utils.log import get_task_logger
from discord_webhook import DiscordEmbed, DiscordWebhook
from django.db.models import Q
from dotted_dict import DottedDict

from reNgine.common_serializers import *
from reNgine.definitions import *
from reNgine.settings import *
from scanEngine.models import *
from dashboard.models import *
from startScan.models import *
from targetApp.models import *
from reNgine.utilities import is_valid_url


logger = get_task_logger(__name__)
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
		with open(os.path.join(results_dir, f"{engine.engine_name}.yaml"), 'w') as f:
			f.write(engine.yaml_configuration)

def load_custom_scan_engines(results_dir):
	"""Load custom scan engines from YAML files. The filename without .yaml will
	be used as the engine name.

	Args:
		results_dir (str): Results directory containing engines configs.
	"""
	config_paths = [
		f for f in os.listdir(results_dir)
		if os.path.isfile(os.path.join(results_dir, f)) and f.endswith('.yaml')
	]
	for path in config_paths:
		engine_name = os.path.splitext(os.path.basename(path))[0]
		full_path = os.path.join(results_dir, path)
		with open(full_path, 'r') as f:
			yaml_configuration = f.read()

		engine, _ = EngineType.objects.get_or_create(engine_name=engine_name)
		engine.yaml_configuration = yaml_configuration
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

def get_subdomains(write_filepath=None, exclude_subdomains=False, ctx={}):
	"""Get Subdomain objects from DB.

	Args:
		write_filepath (str): Write info back to a file.
		exclude_subdomains (bool): Exclude subdomains, only return subdomain matching domain.
		ctx (dict): ctx

	Returns:
		list: List of subdomains matching query.
	"""
	domain_id = ctx.get('domain_id')
	scan_id = ctx.get('scan_history_id')
	subdomain_id = ctx.get('subdomain_id')
	exclude_subdomains = ctx.get('exclude_subdomains', False)
	url_filter = ctx.get('url_filter', '')
	domain = Domain.objects.filter(pk=domain_id).first()
	scan = ScanHistory.objects.filter(pk=scan_id).first()

	query = Subdomain.objects
	if domain:
		query = query.filter(target_domain=domain)
	if scan:
		query = query.filter(scan_history=scan)
	if subdomain_id:
		query = query.filter(pk=subdomain_id)
	elif domain and exclude_subdomains:
		query = query.filter(name=domain.name)
	subdomain_query = query.distinct('name').order_by('name')
	subdomains = [
		subdomain.name
		for subdomain in subdomain_query.all()
		if subdomain.name
	]
	if not subdomains:
		logger.error('No subdomains were found in query !')

	if url_filter:
		subdomains = [f'{subdomain}/{url_filter}' for subdomain in subdomains]

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
		is_alive=False,
		is_uncrawled=False,
		strict=False,
		ignore_files=False,
		write_filepath=None,
		exclude_subdomains=False,
		get_only_default_urls=False,
		ctx={}):
	"""Get HTTP urls from EndPoint objects in DB. Support filtering out on a
	specific path.

	Args:
		is_alive (bool): If True, select only alive urls.
		is_uncrawled (bool): If True, select only urls that have not been crawled.
		write_filepath (str): Write info back to a file.
		get_only_default_urls (bool):

	Returns:
		list: List of URLs matching query.
	"""
	domain_id = ctx.get('domain_id')
	scan_id = ctx.get('scan_history_id')
	subdomain_id = ctx.get('subdomain_id')
	url_filter = ctx.get('url_filter', '')
	domain = Domain.objects.filter(pk=domain_id).first()
	scan = ScanHistory.objects.filter(pk=scan_id).first()

	query = EndPoint.objects
	if domain:
		query = query.filter(target_domain=domain)
	if scan:
		query = query.filter(scan_history=scan)
	if subdomain_id:
		query = query.filter(subdomain__id=subdomain_id)
	elif exclude_subdomains and domain:
		query = query.filter(http_url=domain.http_url)
	if get_only_default_urls:
		query = query.filter(is_default=True)

	# If is_uncrawled is True, select only endpoints that have not been crawled
	# yet (no status)
	if is_uncrawled:
		query = query.filter(http_status__isnull=True)

	# If a path is passed, select only endpoints that contains it
	if url_filter and domain:
		url = f'{domain.name}{url_filter}'
		if strict:
			query = query.filter(http_url=url)
		else:
			query = query.filter(http_url__contains=url)

	# Select distinct endpoints and order
	endpoints = query.distinct('http_url').order_by('http_url').all()

	# If is_alive is True, select only endpoints that are alive
	if is_alive:
		endpoints = [e for e in endpoints if e.is_alive]

	# Grab only http_url from endpoint objects
	endpoints = [e.http_url for e in endpoints if is_valid_url(e.http_url)]
	if ignore_files: # ignore all files
		extensions_path = f'{RENGINE_HOME}/fixtures/extensions.txt'
		with open(extensions_path, 'r') as f:
			extensions = tuple(f.strip() for f in f.readlines())
		endpoints = [e for e in endpoints if not urlparse(e).path.endswith(extensions)]

	if not endpoints:
		logger.error(f'No endpoints were found in query !')

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
	# Check if the URL has a scheme. If not, add a temporary one to prevent empty netloc.
	if "://" not in url:
		url = "http://" + url

	url_obj = urlparse(url.strip())
	return url_obj.netloc.split(':')[0]


def get_domain_from_subdomain(subdomain):
	"""Get domain from subdomain.

	Args:
		subdomain (str): Subdomain name.

	Returns:
		str: Domain name.
	"""
	# ext = tldextract.extract(subdomain)
	# return '.'.join(ext[1:3])

	if not validators.domain(subdomain):
		return None
	
	# Use tldextract to parse the subdomain
	extracted = tldextract.extract(subdomain)

	# if tldextract recognized the tld then its the final result
	if extracted.suffix:
		domain = f"{extracted.domain}.{extracted.suffix}"
	else:
		# Fallback method for unknown TLDs, like .clouds or .local etc
		parts = subdomain.split('.')
		if len(parts) >= 2:
			domain = '.'.join(parts[-2:])
		else:
			return None
		
	# Validate the domain before returning
	return domain if validators.domain(domain) else None



def sanitize_url(http_url):
	"""Removes HTTP ports 80 and 443 from HTTP URL because it's ugly.

	Args:
		http_url (str): Input HTTP URL.

	Returns:
		str: Stripped HTTP URL.
	"""
	# Check if the URL has a scheme. If not, add a temporary one to prevent empty netloc.
	if "://" not in http_url:
		http_url = "http://" + http_url
	url = urlparse(http_url)

	if url.netloc.endswith(':80'):
		url = url._replace(netloc=url.netloc.replace(':80', ''))
	elif url.netloc.endswith(':443'):
		url = url._replace(scheme=url.scheme.replace('http', 'https'))
		url = url._replace(netloc=url.netloc.replace(':443', ''))
	return url.geturl().rstrip('/')

def extract_path_from_url(url):
	parsed_url = urlparse(url)

	# Reconstruct the URL without scheme and netloc
	reconstructed_url = parsed_url.path

	if reconstructed_url.startswith('/'):
		reconstructed_url = reconstructed_url[1:]  # Remove the first slash

	if parsed_url.params:
		reconstructed_url += ';' + parsed_url.params
	if parsed_url.query:
		reconstructed_url += '?' + parsed_url.query
	if parsed_url.fragment:
		reconstructed_url += '#' + parsed_url.fragment

	return reconstructed_url

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

def remove_ansi_escape_sequences(text):
	# Regular expression to match ANSI escape sequences
	ansi_escape_pattern = r'\x1b\[.*?m'

	# Use re.sub() to replace the ANSI escape sequences with an empty string
	plain_text = re.sub(ansi_escape_pattern, '', text)
	return plain_text

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
		find_dir += f'_{port}'

	# subdomain may also have port number, and is stored in dir as _port

	cms_dir_path =  f'/usr/src/github/CMSeeK/Result/{find_dir}'
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
			logger.error(e)

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

def send_lark_message(message):
	"""Send lark message.

	Args:
		message (str): Message.
	"""
	headers = {'content-type': 'application/json'}
	message = {"msg_type":"interactive","card":{"elements":[{"tag":"div","text":{"content":message,"tag":"lark_md"}}]}}
	notif = Notification.objects.first()
	do_send = (
		notif and
		notif.send_to_lark and
		notif.lark_hook_url)
	if not do_send:
		return
	hook_url = notif.lark_hook_url
	requests.post(url=hook_url, data=json.dumps(message), headers=headers)

def send_discord_message(
		message,
		title='',
		severity=None,
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
			rate_limit_retry=False,
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
		if url:
			embed.set_url(url)
		if severity:
			embed.set_color(DISCORD_SEVERITY_COLORS[severity])
		embed.set_description(message)
		embed.set_timestamp()
		existing_fields_dict = {field['name']: field['value'] for field in embed.fields}
		logger.debug(''.join([f'\n\t{k}: {v}' for k, v in fields.items()]))
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

					if len(value) > 1024: # character limit for embed field
						value = value[0:1016] + '\n[...]'

				# Update existing embed
				ix = embed.fields.index(field)
				embed.fields[ix]['value'] = value

			else:
				embed.add_embed_field(**new_field)

		webhook.add_embed(embed)

		# Add webhook and embed objects to cache, so we can pick them up later
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
		errors = json.loads(
			response.content.decode('utf-8'))
		wh_sleep = (int(errors['retry_after']) / 1000) + 0.15
		sleep(wh_sleep)
		send_discord_message(
				message,
				title,
				severity,
				url,
				files,
				fields,
				fields_append)
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


def get_scan_url(scan_id=None, subscan_id=None):
	if scan_id:
		return f'https://{DOMAIN_NAME}/scan/detail/{scan_id}'
	return None


def get_scan_fields(engine, scan, subscan=None, status='RUNNING', tasks=[]):
	scan_obj = subscan if subscan else scan
	if subscan:
		tasks_h = f'`{subscan.type}`'
		host = subscan.subdomain.name
		scan_obj = subscan
	else:
		tasks_h = '• ' + '\n• '.join(f'`{task.name}`' for task in tasks) if tasks else ''
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

	fields['Host'] = host
	if tasks:
		fields['Tasks'] = tasks_h

	return fields


def get_task_title(task_name, scan_id=None, subscan_id=None):
	if scan_id:
		prefix = f'#{scan_id}'
		if subscan_id:
			prefix += f'-#{subscan_id}'
		return f'`{prefix}` - `{task_name}`'
	return f'`{task_name}` [unbound]'


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
		path += f'/#{scan_history_id}'
		if subscan_id:
			path += f'-#{subscan_id}'
	path += f'-{task_name}.txt'
	return path


def fmt_traceback(exc):
	return '\n'.join(traceback.format_exception(None, exc, exc.__traceback__))


#--------------#
# CLI BUILDERS #
#--------------#

def _build_cmd(cmd, options, flags, sep=" "):
	for k,v in options.items():
		if not v:
			continue
		cmd += f" {k}{sep}{v}"

	for flag in flags:
		if not flag:
			continue
		cmd += f" --{flag}"

	return cmd

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

	options = {
		"-sV": service_detection,
		"-p": ports,
		"--script": script,
		"--script-args": script_args,
		"--max-rate": max_rate,
		"-oX": output_file
	}
	cmd = _build_cmd(cmd, options, flags)

	if not input_file:
		cmd += f" {host}" if host else ""
	else:
		cmd += f" -iL {input_file}"

	return cmd


def xml2json(xml):
	with open(xml) as xml_file:
		xml_content = xml_file.read()
	return xmltodict.parse(xml_content)


def reverse_whois(lookup_keyword):
	domains = []
	'''
		This function will use viewdns to fetch reverse whois info
		Input: lookup keyword like email or registrar name
		Returns a list of domains as string.
	'''
	logger.info(f'Querying reverse whois for {lookup_keyword}')
	url = f"https://viewdns.info:443/reversewhois/?q={lookup_keyword}"
	headers = {
		"Sec-Ch-Ua": "\" Not A;Brand\";v=\"99\", \"Chromium\";v=\"104\"",
		"Sec-Ch-Ua-Mobile": "?0",
		"Sec-Ch-Ua-Platform": "\"Linux\"",
		"Upgrade-Insecure-Requests": "1",
		"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.5112.102 Safari/537.36",
		"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
		"Sec-Fetch-Site": "same-origin",
		"Sec-Fetch-Mode": "navigate",
		"Sec-Fetch-User": "?1",
		"Sec-Fetch-Dest": "document",
		"Referer": "https://viewdns.info/",
		"Accept-Encoding": "gzip, deflate",
		"Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8"
	}
	response = requests.get(url, headers=headers)
	soup = BeautifulSoup(response.content, 'lxml')
	table = soup.find("table", {"border" : "1"})
	try:
		for row in table or []:
			dom = row.findAll('td')[0].getText()
			# created_on = row.findAll('td')[1].getText() TODO: add this in 3.0
			if dom == 'Domain Name':
				continue
			domains.append(dom)
	except Exception as e:
		logger.error(f'Error while fetching reverse whois info: {e}')
	return domains


def get_domain_historical_ip_address(domain):
	ips = []
	'''
		This function will use viewdns to fetch historical IP address
		for a domain
	'''
	logger.info(f'Fetching historical IP address for domain {domain}')
	url = f"https://viewdns.info/iphistory/?domain={domain}"
	headers = {
		"Sec-Ch-Ua": "\" Not A;Brand\";v=\"99\", \"Chromium\";v=\"104\"",
		"Sec-Ch-Ua-Mobile": "?0",
		"Sec-Ch-Ua-Platform": "\"Linux\"",
		"Upgrade-Insecure-Requests": "1",
		"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.5112.102 Safari/537.36",
		"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
		"Sec-Fetch-Site": "same-origin",
		"Sec-Fetch-Mode": "navigate",
		"Sec-Fetch-User": "?1",
		"Sec-Fetch-Dest": "document",
		"Referer": "https://viewdns.info/",
		"Accept-Encoding": "gzip, deflate",
		"Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8"
	}
	response = requests.get(url, headers=headers)
	soup = BeautifulSoup(response.content, 'lxml')
	table = soup.find("table", {"border" : "1"})					   
	for row in table or []:
		ip = row.findAll('td')[0].getText()
		location = row.findAll('td')[1].getText()
		owner = row.findAll('td')[2].getText()
		last_seen = row.findAll('td')[2].getText()
		if ip == 'IP Address':
			continue
		ips.append(
			{
				'ip': ip,
				'location': location,
				'owner': owner,
				'last_seen': last_seen,
			}
		)
	return ips


def get_open_ai_key():
	openai_key = OpenAiAPIKey.objects.all()
	return openai_key[0] if openai_key else None


def get_netlas_key():
	netlas_key = NetlasAPIKey.objects.all()
	return netlas_key[0] if netlas_key else None


def get_chaos_key():
	chaos_key = ChaosAPIKey.objects.all()
	return chaos_key[0] if chaos_key else None


def get_hackerone_key_username():
	"""
		Get the HackerOne API key username from the database.
		Returns: a tuple of the username and api key
	"""
	hackerone_key = HackerOneAPIKey.objects.all()
	return (hackerone_key[0].username, hackerone_key[0].key) if hackerone_key else None


def parse_llm_vulnerability_report(report):
	report = report.replace('**', '')
	data = {}
	sections = re.split(r'\n(?=(?:Description|Impact|Remediation|References):)', report.strip())
	
	try:
		for section in sections:
			if not section.strip():
				continue
			
			section_title, content = re.split(r':\n', section.strip(), maxsplit=1)
			
			if section_title == 'Description':
				data['description'] = content.strip()
			elif section_title == 'Impact':
				data['impact'] = content.strip()
			elif section_title == 'Remediation':
				data['remediation'] = content.strip()
			elif section_title == 'References':
				data['references'] = [ref.strip() for ref in content.split('\n') if ref.strip()]
	except Exception as e:
		return data
	
	return data


def create_scan_object(host_id, engine_id, initiated_by_id=None):
	'''
	create task with pending status so that celery task will execute when
	threads are free
	Args:
		host_id: int: id of Domain model
		engine_id: int: id of EngineType model
		initiated_by_id: int : id of User model (Optional)
	'''
	# get current time
	current_scan_time = timezone.now()
	# fetch engine and domain object
	engine = EngineType.objects.get(pk=engine_id)
	domain = Domain.objects.get(pk=host_id)
	scan = ScanHistory()
	scan.scan_status = INITIATED_TASK
	scan.domain = domain
	scan.scan_type = engine
	scan.start_scan_date = current_scan_time
	if initiated_by_id:
		user = User.objects.get(pk=initiated_by_id)
		scan.initiated_by = user
	scan.save()
	# save last scan date for domain model
	domain.start_scan_date = current_scan_time
	domain.save()
	return scan.id


def get_port_service_description(port):
	"""
		Retrieves the standard service name and description for a given port 
		number using whatportis and the builtin socket library as fallback.

		Args:
			port (int or str): The port number to look up. 
				Can be an integer or a string representation of an integer.

		Returns:
			dict: A dictionary containing the service name and description for the port number.
	"""
	logger.info('Fetching Port Service Name and Description')
	try:
		port = int(port)
		whatportis_result = whatportis.get_ports(str(port))
		
		if whatportis_result and whatportis_result[0].name:
			return {
				"service_name": whatportis_result[0].name,
				"description": whatportis_result[0].description
			}
		else:
			try:
				service = socket.getservbyport(port)
				return {
					"service_name": service,
					"description": "" # Keep description blank when using socket
				}
			except OSError:
				# If both whatportis and socket fail
				return {
					"service_name": "",
					"description": ""
				}
	except:
		# port is not a valid int or any other exception
		return {
			"service_name": "",
			"description": ""
		}


def update_or_create_port(port_number, service_name=None, description=None):
	"""
		Updates or creates a new Port object with the provided information to 
		avoid storing duplicate entries when service or description information is updated.

		Args:
			port_number (int): The port number to update or create.
			service_name (str, optional): The name of the service associated with the port.
			description (str, optional): A description of the service associated with the port.

		Returns:
			Tuple: A tuple containing the Port object and a boolean indicating whether the object was created.
	"""
	created = False
	try:
		port = Port.objects.get(number=port_number)
		
		# avoid updating None values in service and description if they already exist
		if service_name is not None and port.service_name != service_name:
			port.service_name = service_name
		if description is not None and port.description != description:
			port.description = description
		port.save()	
	except Port.DoesNotExist:
		# for cases if the port doesn't exist, create a new one
		port = Port.objects.create(
			number=port_number,
			service_name=service_name,
			description=description
		)
		created = True
	finally:
		return port, created
	

def exclude_urls_by_patterns(exclude_paths, urls):
	"""
		Filter out URLs based on a list of exclusion patterns provided from user
		
		Args:
			exclude_patterns (list of str): A list of patterns to exclude. 
			These can be plain path or regex.
			urls (list of str): A list of URLs to filter from.
			
		Returns:
			list of str: A new list containing URLs that don't match any exclusion pattern.
	"""
	logger.info('exclude_urls_by_patterns')
	if not exclude_paths:
		# if no exclude paths are passed and is empty list return all urls as it is
		return urls
	
	compiled_patterns = []
	for path in exclude_paths:
		# treat each path as either regex or plain path
		try:
			raw_pattern = r"{}".format(path)
			compiled_patterns.append(re.compile(raw_pattern))
		except re.error:
			compiled_patterns.append(path)

	filtered_urls = []
	for url in urls:
		exclude = False
		for pattern in compiled_patterns:
			if isinstance(pattern, re.Pattern):
				if pattern.search(url):
					exclude = True
					break
			else:
				if pattern in url: #if the word matches anywhere in url exclude
					exclude = True
					break
		
		# if none conditions matches then add the url to filtered urls
		if not exclude:
			filtered_urls.append(url)

	return filtered_urls
	

def get_domain_info_from_db(target):
	"""
		Retrieves the Domain object from the database using the target domain name.

		Args:
			target (str): The domain name to search for.

		Returns:
			Domain: The Domain object if found, otherwise None.
	"""
	try:
		domain = Domain.objects.get(name=target)
		if not domain.insert_date:
			domain.insert_date = timezone.now()
			domain.save()
		return extract_domain_info(domain)
	except Domain.DoesNotExist:
		return None
	
def extract_domain_info(domain):
	"""
		Extract domain info from the domain_info_db.
		Args:
			domain: Domain object

		Returns:
			DottedDict: The domain info object.
	"""
	if not domain:
		return DottedDict()
	
	domain_name = domain.name
	domain_info_db = domain.domain_info
	
	try:
		domain_info = DottedDict({
			'dnssec': domain_info_db.dnssec,
			'created': domain_info_db.created,
			'updated': domain_info_db.updated,
			'expires': domain_info_db.expires,
			'geolocation_iso': domain_info_db.geolocation_iso,
			'status': [status.name for status in domain_info_db.status.all()],
			'whois_server': domain_info_db.whois_server,
			'ns_records': [ns.name for ns in domain_info_db.name_servers.all()],
		})

		# Extract registrar info
		registrar = domain_info_db.registrar
		if registrar:
			domain_info.update({
				'registrar_name': registrar.name,
				'registrar_phone': registrar.phone,
				'registrar_email': registrar.email,
				'registrar_url': registrar.url,
			})

		# Extract registration info (registrant, admin, tech)
		for role in ['registrant', 'admin', 'tech']:
			registration = getattr(domain_info_db, role)
			if registration:
				domain_info.update({
					f'{role}_{key}': getattr(registration, key)
					for key in ['name', 'id_str', 'organization', 'city', 'state', 'zip_code', 
								'country', 'phone', 'fax', 'email', 'address']
				})

		# Extract DNS records
		dns_records = domain_info_db.dns_records.all()
		for record_type in ['a', 'txt', 'mx']:
			domain_info[f'{record_type}_records'] = [
				record.name for record in dns_records if record.type == record_type
			]

		# Extract related domains and TLDs
		domain_info.update({
			'related_tlds': [domain.name for domain in domain_info_db.related_tlds.all()],
			'related_domains': [domain.name for domain in domain_info_db.related_domains.all()],
		})

		# Extract historical IPs
		domain_info['historical_ips'] = [
			{
				'ip': ip.ip,
				'owner': ip.owner,
				'location': ip.location,
				'last_seen': ip.last_seen
			}
			for ip in domain_info_db.historical_ips.all()
		]

		domain_info['target'] = domain_name
	except Exception as e:
		logger.error(f'Error while extracting domain info: {e}')
		domain_info = DottedDict()

	return domain_info


def format_whois_response(domain_info):
	"""
		Format the domain info for the whois response.
		Args:
			domain_info (DottedDict): The domain info object.
		Returns:
			dict: The formatted whois response.	
	"""
	return {
		'status': True,
		'target': domain_info.get('target'),
		'dnssec': domain_info.get('dnssec'),
		'created': domain_info.get('created'),
		'updated': domain_info.get('updated'),
		'expires': domain_info.get('expires'),
		'geolocation_iso': domain_info.get('registrant_country'),
		'domain_statuses': domain_info.get('status'),
		'whois_server': domain_info.get('whois_server'),
		'dns': {
			'a': domain_info.get('a_records'),
			'mx': domain_info.get('mx_records'),
			'txt': domain_info.get('txt_records'),
		},
		'registrar': {
			'name': domain_info.get('registrar_name'),
			'phone': domain_info.get('registrar_phone'),
			'email': domain_info.get('registrar_email'),
			'url': domain_info.get('registrar_url'),
		},
		'registrant': {
			'name': domain_info.get('registrant_name'),
			'id': domain_info.get('registrant_id'),
			'organization': domain_info.get('registrant_organization'),
			'address': domain_info.get('registrant_address'),
			'city': domain_info.get('registrant_city'),
			'state': domain_info.get('registrant_state'),
			'zipcode': domain_info.get('registrant_zip_code'),
			'country': domain_info.get('registrant_country'),
			'phone': domain_info.get('registrant_phone'),
			'fax': domain_info.get('registrant_fax'),
			'email': domain_info.get('registrant_email'),
		},
		'admin': {
			'name': domain_info.get('admin_name'),
			'id': domain_info.get('admin_id'),
			'organization': domain_info.get('admin_organization'),
			'address':domain_info.get('admin_address'),
			'city': domain_info.get('admin_city'),
			'state': domain_info.get('admin_state'),
			'zipcode': domain_info.get('admin_zip_code'),
			'country': domain_info.get('admin_country'),
			'phone': domain_info.get('admin_phone'),
			'fax': domain_info.get('admin_fax'),
			'email': domain_info.get('admin_email'),
		},
		'technical_contact': {
			'name': domain_info.get('tech_name'),
			'id': domain_info.get('tech_id'),
			'organization': domain_info.get('tech_organization'),
			'address': domain_info.get('tech_address'),
			'city': domain_info.get('tech_city'),
			'state': domain_info.get('tech_state'),
			'zipcode': domain_info.get('tech_zip_code'),
			'country': domain_info.get('tech_country'),
			'phone': domain_info.get('tech_phone'),
			'fax': domain_info.get('tech_fax'),
			'email': domain_info.get('tech_email'),
		},
		'nameservers': domain_info.get('ns_records'),
		'related_domains': domain_info.get('related_domains'),
		'related_tlds': domain_info.get('related_tlds'),
		'historical_ips': domain_info.get('historical_ips'),
	}


def parse_whois_data(domain_info, whois_data):
	"""Parse WHOIS data and update domain_info."""
	whois = whois_data.get('whois', {})
	dns = whois_data.get('dns', {})

	# Parse basic domain information
	domain_info.update({
		'created': whois.get('created_date', None),
		'expires': whois.get('expiration_date', None),
		'updated': whois.get('updated_date', None),
		'whois_server': whois.get('whois_server', None),
		'dnssec': bool(whois.get('dnssec', False)),
		'status': whois.get('status', []),
	})

	# Parse registrar information
	parse_registrar_info(domain_info, whois.get('registrar', {}))

	# Parse registration information
	for role in ['registrant', 'administrative', 'technical']:
		parse_registration_info(domain_info, whois.get(role, {}), role)

	# Parse DNS records
	parse_dns_records(domain_info, dns)

	# Parse name servers
	domain_info.ns_records = dns.get('ns', [])


def parse_registrar_info(domain_info, registrar):
	"""Parse registrar information."""
	domain_info.update({
		'registrar_name': registrar.get('name', None),
		'registrar_email': registrar.get('email', None),
		'registrar_phone': registrar.get('phone', None),
		'registrar_url': registrar.get('url', None),
	})

def parse_registration_info(domain_info, registration, role):
	"""Parse registration information for registrant, admin, and tech contacts."""
	role_prefix = role if role != 'administrative' else 'admin'
	domain_info.update({
		f'{role_prefix}_{key}': value
		for key, value in registration.items()
		if key in ['name', 'id', 'organization', 'street', 'city', 'province', 'postal_code', 'country', 'phone', 'fax']
	})

	# Handle email separately to apply regex
	email = registration.get('email')
	if email:
		email_match = EMAIL_REGEX.search(str(email))
		domain_info[f'{role_prefix}_email'] = email_match.group(0) if email_match else None

def parse_dns_records(domain_info, dns):
	"""Parse DNS records."""
	domain_info.update({
		'mx_records': dns.get('mx', []),
		'txt_records': dns.get('txt', []),
		'a_records': dns.get('a', []),
		'ns_records': dns.get('ns', []),
	})


def save_domain_info_to_db(target, domain_info):
	"""Save domain info to the database."""
	if Domain.objects.filter(name=target).exists():
		domain, _ = Domain.objects.get_or_create(name=target)
		
		# Create or update DomainInfo
		domain_info_obj, created = DomainInfo.objects.get_or_create(domain=domain)
		
		# Update basic domain information
		domain_info_obj.dnssec = domain_info.get('dnssec', False)
		domain_info_obj.created = domain_info.get('created')
		domain_info_obj.updated = domain_info.get('updated')
		domain_info_obj.expires = domain_info.get('expires')
		domain_info_obj.whois_server = domain_info.get('whois_server')
		domain_info_obj.geolocation_iso = domain_info.get('registrant_country')

		# Save or update Registrar
		registrar, _ = Registrar.objects.get_or_create(
			name=domain_info.get('registrar_name', ''),
			defaults={
				'email': domain_info.get('registrar_email'),
				'phone': domain_info.get('registrar_phone'),
				'url': domain_info.get('registrar_url'),
			}
		)
		domain_info_obj.registrar = registrar

		# Save or update Registrations (registrant, admin, tech)
		for role in ['registrant', 'admin', 'tech']:
			registration, _ = DomainRegistration.objects.get_or_create(
				name=domain_info.get(f'{role}_name', ''),
				defaults={
					'organization': domain_info.get(f'{role}_organization'),
					'address': domain_info.get(f'{role}_address'),
					'city': domain_info.get(f'{role}_city'),
					'state': domain_info.get(f'{role}_state'),
					'zip_code': domain_info.get(f'{role}_zip_code'),
					'country': domain_info.get(f'{role}_country'),
					'email': domain_info.get(f'{role}_email'),
					'phone': domain_info.get(f'{role}_phone'),
					'fax': domain_info.get(f'{role}_fax'),
					'id_str': domain_info.get(f'{role}_id'),
				}
			)
			setattr(domain_info_obj, role, registration)

		# Save domain statuses
		domain_info_obj.status.clear()
		for status in domain_info.get('status', []):
			status_obj, _ = WhoisStatus.objects.get_or_create(name=status)
			domain_info_obj.status.add(status_obj)

		# Save name servers
		domain_info_obj.name_servers.clear()
		for ns in domain_info.get('ns_records', []):
			ns_obj, _ = NameServer.objects.get_or_create(name=ns)
			domain_info_obj.name_servers.add(ns_obj)

		# Save DNS records
		domain_info_obj.dns_records.clear()
		for record_type in ['a', 'mx', 'txt']:
			for record in domain_info.get(f'{record_type}_records', []):
				dns_record, _ = DNSRecord.objects.get_or_create(
					name=record,
					type=record_type
				)
				domain_info_obj.dns_records.add(dns_record)

		# Save related domains and TLDs
		domain_info_obj.related_domains.clear()
		for related_domain in domain_info.get('related_domains', []):
			related_domain_obj, _ = RelatedDomain.objects.get_or_create(name=related_domain)
			domain_info_obj.related_domains.add(related_domain_obj)

		domain_info_obj.related_tlds.clear()
		for related_tld in domain_info.get('related_tlds', []):
			related_tld_obj, _ = RelatedDomain.objects.get_or_create(name=related_tld)
			domain_info_obj.related_tlds.add(related_tld_obj)

		# Save historical IPs
		domain_info_obj.historical_ips.clear()
		for ip_info in domain_info.get('historical_ips', []):
			historical_ip, _ = HistoricalIP.objects.get_or_create(
				ip=ip_info['ip'],
				defaults={
					'owner': ip_info.get('owner'),
					'location': ip_info.get('location'),
					'last_seen': ip_info.get('last_seen'),
				}
			)
			domain_info_obj.historical_ips.add(historical_ip)

		# Save the DomainInfo object
		domain_info_obj.save()

		# Update the Domain object with the new DomainInfo
		domain.domain_info = domain_info_obj
		domain.save()

		return domain_info_obj


def create_inappnotification(
		title,
		description,
		notification_type=SYSTEM_LEVEL_NOTIFICATION,
		project_slug=None,
		icon="mdi-bell",
		is_read=False,
		status='info',
		redirect_link=None,
		open_in_new_tab=False
):
	"""
		This function will create an inapp notification
		Inapp Notification not to be confused with Notification model 
		that is used for sending alerts on telegram, slack etc.
		Inapp notification is used to show notification on the web app

		Args: 
			title: str: Title of the notification
			description: str: Description of the notification
			notification_type: str: Type of the notification, it can be either
				SYSTEM_LEVEL_NOTIFICATION or PROJECT_LEVEL_NOTIFICATION
			project_slug: str: Slug of the project, if notification is PROJECT_LEVEL_NOTIFICATION
			icon: str: Icon of the notification, only use mdi icons
			is_read: bool: Whether the notification is read or not, default is False
			status: str: Status of the notification (success, info, warning, error), default is info
			redirect_link: str: Link to redirect when notification is clicked
			open_in_new_tab: bool: Whether to open the redirect link in a new tab, default is False

		Returns:
			ValueError: if error
			InAppNotification: InAppNotification object if successful
	"""
	logger.info('Creating InApp Notification with title: %s', title)
	if notification_type not in [SYSTEM_LEVEL_NOTIFICATION, PROJECT_LEVEL_NOTIFICATION]:
		raise ValueError("Invalid notification type")
	
	if status not in [choice[0] for choice in NOTIFICATION_STATUS_TYPES]:
		raise ValueError("Invalid notification status")
	
	project = None
	if notification_type == PROJECT_LEVEL_NOTIFICATION:
		if not project_slug:
			raise ValueError("Project slug is required for project level notification")
		try:
			project = Project.objects.get(slug=project_slug)
		except Project.DoesNotExist as e:
			raise ValueError(f"No project exists: {e}")
		
	notification = InAppNotification(
		title=title,
		description=description,
		notification_type=notification_type,
		project=project,
		icon=icon,
		is_read=is_read,
		status=status,
		redirect_link=redirect_link,
		open_in_new_tab=open_in_new_tab
	)
	notification.save()
	return notification

def get_ip_info(ip_address):
	is_ipv4 = bool(validators.ipv4(ip_address))
	is_ipv6 = bool(validators.ipv6(ip_address))
	ip_data = None
	if is_ipv4:
		ip_data = ipaddress.IPv4Address(ip_address)
	elif is_ipv6:
		ip_data = ipaddress.IPv6Address(ip_address)
	else:
		return None
	return ip_data

def get_ips_from_cidr_range(target):
	try:
		return [str(ip) for ip in ipaddress.IPv4Network(target, False)]
	except Exception as e:
		logger.error(f'{target} is not a valid CIDR range. Skipping.')

import re
import os
import validators

from celery._state import get_current_task
from celery.utils.log import ColorFormatter


def is_safe_path(basedir, path, follow_symlinks=True):
	# Source: https://security.openstack.org/guidelines/dg_using-file-paths.html
	# resolves symbolic links
	if follow_symlinks:
		matchpath = os.path.realpath(path)
	else:
		matchpath = os.path.abspath(path)
	return basedir == os.path.commonpath((basedir, matchpath))


# Source: https://stackoverflow.com/a/10408992
def remove_lead_and_trail_slash(s):
	if s.startswith('/'):
		s = s[1:]
	if s.endswith('/'):
		s = s[:-1]
	return s


def get_time_taken(latest, earlier):
	duration = latest - earlier
	days, seconds = duration.days, duration.seconds
	hours = days * 24 + seconds // 3600
	minutes = (seconds % 3600) // 60
	seconds = seconds % 60
	if not hours and not minutes:
		return f'{seconds} seconds'
	elif not hours:
		return f'{minutes} minutes'
	elif not minutes:
		return f'{hours} hours'
	return f'{hours} hours {minutes} minutes'

# Check if value is a simple string, a string with commas, a list [], a tuple (), a set {} and return an iterable
def return_iterable(string):
	if not isinstance(string, (list, tuple)):
		string = [string]

	return string


# Logging formatters

class RengineTaskFormatter(ColorFormatter):

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		try:
			self.get_current_task = get_current_task
		except ImportError:
			self.get_current_task = lambda: None

	def format(self, record):
		task = self.get_current_task()
		if task and task.request:
			task_name = '/'.join(task.name.replace('tasks.', '').split('.'))
			record.__dict__.update(task_id=task.request.id,
								   task_name=task_name)
		else:
			record.__dict__.setdefault('task_name', f'{record.module}.{record.funcName}')
			record.__dict__.setdefault('task_id', '')
		return super().format(record)


def get_gpt_vuln_input_description(title, path):
	vulnerability_description = ''
	vulnerability_description += f'Vulnerability Title: {title}'
	# gpt gives concise vulnerability description when a vulnerable URL is provided
	vulnerability_description += f'\nVulnerable URL: {path}'

	return vulnerability_description


def replace_nulls(obj):
	if isinstance(obj, str):
		return obj.replace("\x00", "")
	elif isinstance(obj, list):
		return [replace_nulls(item) for item in obj]
	elif isinstance(obj, dict):
		return {key: replace_nulls(value) for key, value in obj.items()}
	else:
		return obj


def is_valid_url(url, validate_only_http_scheme=True):
	"""
		Validate a URL/endpoint

		Args:
		url (str): The URL to validate.
		validate_only_http_scheme (bool): If True, only validate HTTP/HTTPS URLs.

		Returns:
		bool: True if the URL is valid, False otherwise.
	"""
	# no urls returns false
	if not url:
		return False
	
	# urls with space are not valid urls
	if ' ' in url:
		return False

	if validators.url(url):
		# check for scheme, for example ftp:// can be a valid url but may not be required to crawl etc
		if validate_only_http_scheme:
			return url.startswith('http://') or url.startswith('https://')
		return True
	return False


class SubdomainScopeChecker:
	"""
		SubdomainScopeChecker is a utility class to check if a subdomain is in scope or not.
		it supports both regex and string matching.
	"""

	def __init__(self, patterns):
		self.regex_patterns = set()
		self.plain_patterns = set()
		self.load_patterns(patterns)

	def load_patterns(self, patterns):
		"""
			Load patterns into the checker.

			Args:
				patterns (list): List of patterns to load.
			Returns: 
				None
		"""
		for pattern in patterns:
			# skip empty patterns
			if not pattern:
				continue
			try:
				self.regex_patterns.add(re.compile(pattern, re.IGNORECASE))
			except re.error:
				self.plain_patterns.add(pattern.lower())

	def is_out_of_scope(self, subdomain):
		"""
			Check if a subdomain is out of scope.

			Args:
				subdomain (str): The subdomain to check.
			Returns:
				bool: True if the subdomain is out of scope, False otherwise.
		"""
		subdomain = subdomain.lower() # though we wont encounter this, but just in case
		if subdomain in self.plain_patterns:
			return True
		return any(pattern.search(subdomain) for pattern in self.regex_patterns)



def sorting_key(subdomain):
	# sort subdomains based on their http status code with priority 200 < 300 < 400 < rest
	status = subdomain['http_status']
	if 200 <= status <= 299:
		return 1
	elif 300 <= status <= 399:
		return 2
	elif 400 <= status <= 499:
		return 3
	else:
		return 4
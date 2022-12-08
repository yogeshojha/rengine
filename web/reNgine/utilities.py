import os

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
		return '{} seconds'.format(seconds)
	elif not hours:
		return '{} minutes'.format(minutes)
	elif not minutes:
		return '{} hours'.format(hours)
	return '{} hours {} minutes'.format(hours, minutes)


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
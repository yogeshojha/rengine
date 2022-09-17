import json
import os
from sre_constants import SUCCESS
from time import time

import django
from celery import Celery, Task
from celery.app.log import TaskFormatter
from celery.signals import after_setup_task_logger
from celery.utils.log import get_task_logger
from celery.worker.request import Request
from django.utils import timezone
from redis import Redis
from reNgine.definitions import (CELERY_TASK_STATUS_MAP, DYNAMIC_ID,
                                 FAILED_TASK, RUNNING_TASK, SUCCESS_TASK)
from reNgine.settings import (CELERY_RAISE_ON_ERROR, CELERY_TASK_CACHE_ENABLED,
                              CELERY_TASK_CACHE_IGNORE_KWARGS,
                              CELERY_TASK_SKIP_RECORD_ACTIVITY)

cache = Redis.from_url(os.environ['CELERY_BROKER'])
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reNgine.settings')

# db imports only work if django is loaded, so MUST be placed after django setup
django.setup()
from reNgine.common_func import (fmt_traceback, send_file_to_discord_helper, write_traceback)
from scanEngine.models import EngineType
from startScan.models import ScanActivity, ScanHistory, SubScan


def create_scan_activity(scan_history_id, task_id, name, message, status, subscan_id=None):
	scan_history = ScanHistory.objects.get(pk=scan_history_id)
	scan_history.celery_ids.append(task_id)
	scan_history.save()
	scan_activity = ScanActivity()
	scan_activity.scan_of = scan_history
	scan_activity.name = name
	scan_activity.title = message
	scan_activity.time = timezone.now()
	scan_activity.status = status
	scan_activity.save()
	if subscan_id:
		subscan = SubScan.objects.get(pk=subscan_id)
		subscan.celery_ids.append(task_id)
		subscan.save()
	return scan_activity.id


def update_scan_activity(id, status, error=None, traceback=None):
	scan_activity = ScanActivity.objects.filter(id=id)
	if error and len(error) > 300:
		error = error[:288] + '...[trimmed]'
	return scan_activity.update(
			status=status,
			error_message=error,
			traceback=traceback,
			time=timezone.now())


class RengineRequest(Request):
	pass


class RengineTask(Task):
	Request = RengineRequest
	def __call__(self, *args, **kwargs):
		task_name = self.name.split('.')[-1]
		result = None
		error = None
		traceback = None
		logger = get_task_logger(task_name)

		# Check if this task needs to be recorded.
		RECORD_ACTIVITY = (
			self.name not in CELERY_TASK_SKIP_RECORD_ACTIVITY and
			'engine_id' in kwargs and 
			'scan_history_id' in kwargs and
			'activity_id' in kwargs and kwargs['activity_id'] == DYNAMIC_ID
		)
		if RECORD_ACTIVITY:
			# If task is not in engine.tasks, skip it.
			engine_id = kwargs['engine_id']
			if engine_id:
				engine = EngineType.objects.get(pk=engine_id)
				if task_name not in engine.tasks:
					logger.debug(f'{task_name} is not part of this engine tasks. Skipping.')
					return

			# Create ScanActivity for this task
			scan_history_id = kwargs['scan_history_id']
			subscan_id = kwargs.get('subscan_id')
			task_descr = kwargs.pop('description', None) or ' '.join(task_name.split('_')).capitalize()
			activity_id = create_scan_activity(
				scan_history_id=scan_history_id,
				task_id=self.request.id,
				name=task_name,
				message=task_descr,
				subscan_id=subscan_id,
				status=RUNNING_TASK)

			# Set activity id in task kwargs so we can update ScanActivity from
			# within the task
			kwargs['activity_id'] = activity_id 
			logger.warning(f'Task {self.name} status is RUNNING')

		# Check for result in cache and return if hit
		if CELERY_TASK_CACHE_ENABLED:
			args_str = '_'.join([str(arg) for arg in args])
			kwargs_str = '_'.join([f'{k}={v}' for k, v in kwargs.items() if k not in CELERY_TASK_CACHE_IGNORE_KWARGS])
			record_key = f'{self.name}__{args_str}__{kwargs_str}'
			result = cache.get(record_key)
			if result and result != b'null':
				if RECORD_ACTIVITY:
					logger.warning(f'Task {self.name} status is SUCCESS (CACHED)')
					update_scan_activity(activity_id, SUCCESS_TASK)
				return json.loads(result)

		# Execute task
		try:
			result = self.run(*args, **kwargs)
			status = SUCCESS_TASK
		except Exception as exc:
			status = FAILED_TASK
			error = repr(exc)
			traceback = fmt_traceback(exc)
			if CELERY_RAISE_ON_ERROR:
				raise exc
			logger.exception(exc)
		finally:
			status_str = CELERY_TASK_STATUS_MAP[status]
			if RECORD_ACTIVITY:
				msg = f'Task {self.name} status is {status_str}'
				logger.warning(msg)
				# TODO: Add send status notif without a circular import on send_notification
				# notification = Notification.objects.first()
				# send_status = notification.send_scan_status_notif if notification else False
				# if send_status:
				# 	send_notification.delay(msg)
				update_scan_activity(
					activity_id,
					status,
					error=error,
					traceback=traceback)

				if traceback:
					results_dir = kwargs['results_dir']
					scan = ScanHistory.objects.get(pk=scan_history_id)
					output_path = write_traceback(
						traceback,
						results_dir=f'{results_dir}/tracebacks',
						task_name=task_name,
						scan_history=scan,
						subscan_id=subscan_id)
					output_title = output_path.split('/')[-1]
					logger.info(f'Sendin traceback to Discord ...')
					send_file_to_discord_helper(output_path, title=output_title)

		# Set task result in cache
		if CELERY_TASK_CACHE_ENABLED and status == SUCCESS_TASK and result:
			cache.set(record_key, json.dumps(result))
			cache.expire(record_key, 600) # 10mn cache

		return result

	def s(self, *args, **kwargs):
		# TODO: set task status to INIT when creating a signature.
		return super().s(*args, **kwargs)


# Celery app
app = Celery('reNgine', task_cls=RengineTask)
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

@after_setup_task_logger.connect
def setup_task_logger(logger, *args, **kwargs):
	for handler in logger.handlers:
		handler.setFormatter(TaskFormatter('%(task_name)s | %(message)s'))

import json

from celery import Task
from celery.utils.log import get_task_logger
from celery.worker.request import Request
from django.utils import timezone
from redis import Redis
from reNgine.common_func import (fmt_traceback, get_cache_key,
                                 get_output_file_name, get_scan_title, get_task_title,
                                 send_notification_helper, write_traceback)
from reNgine.definitions import *
from reNgine.settings import *
from scanEngine.models import EngineType, Notification
from startScan.models import ScanActivity, ScanHistory, SubScan

cache = Redis.from_url(os.environ['CELERY_BROKER'])

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
	"""A Celery task that is tracked by reNgine. Save task output files and
	tracebacks to RENGINE_RESULTS.
	
	The custom task meta-options are toggleable through environment variables:

	RENGINE_RECORD_ENABLED:
	- Create / update ScanActivity object to track statuses.
	- Send notifications before and after each task (start / end).
	- Send traceback file to reNgine's Discord channel if an exception happened.

	RENGINE_CACHE_ENABLED:
	- Get result from cache if it exists.
	- Set result to cache after a task if no exceptions occured.

	RENGINE_RAISE_ON_ERROR:
	- Raise the actual exception when task fails instead of just logging it.
	"""
	Request = RengineRequest
	def __call__(self, *args, **kwargs):
		result = None
		error = None
		traceback = None
		output_path = None

		# Get task info
		name = self.name.split('.')[-1]
		description = kwargs.get('description') or ' '.join(name.split('_')).capitalize()
		logger = get_task_logger(name)

		# Get reNgine context
		scan_id = kwargs.get('scan_history_id')
		subscan_id = kwargs.get('subscan_id')
		activity_id = kwargs.get('activity_id', DYNAMIC_ID)
		engine_id = kwargs.get('engine_id')
		filename = kwargs.get('filename')
		results_dir = kwargs.get('results_dir', RENGINE_RESULTS)
		if not scan_id:
			raise Exception(
				f'RengineTask Invalid Task:'
				f'scan_history_id must be passed as kwargs !')

		# Set file name if not already set
		if not filename:
			filename = get_output_file_name(scan_id, subscan_id, f'{name}.txt')
			if name == 'screenshot':
				filename = 'Requests.csv'
			kwargs['filename'] = filename

		# Set file output path
		output_path = f'{results_dir}/{filename}'

		if RENGINE_RECORD_ENABLED:
			scan = ScanHistory.objects.get(pk=scan_id)
			notif = Notification.objects.first()

			# If task is not in engine.tasks, skip it.
			if engine_id:
				engine = EngineType.objects.get(pk=engine_id)
				if name not in engine.tasks:
					logger.debug(f'{name} is not part of this engine tasks. Skipping.')
					return

			# Send start log + notification
			msg = f'Task {name} has started'
			title = get_task_title(name, scan_id, subscan_id)
			if notif and notif.send_scan_status_notif:
				fields = {
					'Status': '**RUNNING**'
				}
				send_notification_helper(
					message=msg,
					title=title,
					fields=fields,
					severity='info')

			# Create ScanActivity for this task
			activity_id = create_scan_activity(
				scan_history_id=scan_id,
				task_id=self.request.id,
				name=name,
				message=description,
				subscan_id=subscan_id,
				status=RUNNING_TASK)

			# Set activity id in task kwargs so we can update ScanActivity from
			# within the task if needed.
			kwargs['activity_id'] = activity_id
			logger.warning(f'Task {name} is RUNNING')

		# Check for result in cache and return it if it's a hit
		if RENGINE_CACHE_ENABLED:
			record_key = get_cache_key(name, *args, **kwargs)
			result = cache.get(record_key)
			if result and result != b'null':

				if RENGINE_RECORD_ENABLED:
					logger.warning(f'Task {name} status is SUCCESS (CACHED)')
					update_scan_activity(activity_id, SUCCESS_TASK)

				return json.loads(result)

		# Execute task, catch exceptions and update ScanActivity object after 
		# task has finished running.
		try:
			result = self.run(*args, **kwargs)
			status = SUCCESS_TASK

		except Exception as exc:
			status = FAILED_TASK
			error = repr(exc)
			traceback = fmt_traceback(exc)
			output_path = write_traceback(
					traceback,
					results_dir=f'{results_dir}/tracebacks',
					task_name=name,
					scan_history=scan,
					subscan_id=subscan_id)

			if RENGINE_RAISE_ON_ERROR:
				raise exc
			logger.exception(exc)

		finally:
			status_str = CELERY_TASK_STATUS_MAP[status]

			if RENGINE_RECORD_ENABLED:
				msg = f'Task {self.name} status is {status_str}'
				logger.warning(msg)

				# Update ScanActivity for this task: change task status, add 
				# error and traceback to db when the task failed.
				update_scan_activity(
					activity_id,
					status,
					error=error,
					traceback=traceback)

				# Send task status notification
				if notif and notif.send_scan_status_notif:
					scan = ScanHistory.objects.get(pk=scan_id)

					# Add files to notif
					files = []
					if notif.send_scan_output_file:
						output_title = output_path.split('/')[-1]
						logger.warning(f'Sending output file {output_path} to Discord.')
						if isinstance(result, dict) or isinstance(result, list):
							with open(output_path, 'w') as f:
								json.dump(result, f)
						if output_path and os.path.exists(output_path):
							files = [(output_path, output_title)]
					
					# Send notification
					fields = {'Status': f'**{status_str}**'}
					severity = 'success'
					if status == FAILED_TASK:
						fields['Error'] = error
						fields['Traceback'] = "```\n" + traceback + "\n```"
						severity = 'error'
					send_notification_helper(
						message=msg,
						title=title,
						files=files,
						fields=fields,
						severity=severity)

		# Set task result in cache
		if RENGINE_CACHE_ENABLED and status == SUCCESS_TASK and result:
			cache.set(record_key, json.dumps(result))
			cache.expire(record_key, 600) # 10mn cache

		return result

	def s(self, *args, **kwargs):
		# TODO: set task status to INIT when creating a signature.
		return super().s(*args, **kwargs)
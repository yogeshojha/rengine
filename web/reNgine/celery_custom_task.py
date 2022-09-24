import json

from celery import Task
from celery.utils.log import get_task_logger
from celery.worker.request import Request
from django.utils import timezone
from redis import Redis
from reNgine.common_func import (fmt_traceback, get_output_file_name,
                                 get_task_cache_key, get_traceback_path)
from reNgine.definitions import *
from reNgine.settings import *
from scanEngine.models import EngineType
from startScan.models import ScanActivity, ScanHistory, SubScan

cache = Redis.from_url(os.environ['CELERY_BROKER'])


def create_scan_activity(
		task_celery_id,
		task_name,
		status=None,
		title=None,
		scan_history_id=None,
		subscan_id=None,
		engine_id=None):
	scan = ScanHistory.objects.get(pk=scan_history_id) if scan_history_id else None
	task = ScanActivity(
		name=task_name,
		title=title,
		time=timezone.now(),
		status=status,
		celery_id=task_celery_id)
	if scan:
		task.scan_of = scan
		scan.celery_ids.append(task_celery_id)
		scan.save()
	task.save()
	if subscan_id:
		subscan = SubScan.objects.get(pk=subscan_id)
		subscan.celery_ids.append(task_celery_id)
		subscan.save()

	# Send notification
	from reNgine.tasks import send_task_status_notification
	send_task_status_notification.delay(
		task_name,
		status='RUNNING',
		scan_history_id=scan_history_id,
		engine_id=engine_id,
		subscan_id=subscan_id)

	return task.id


def update_scan_activity(
		id,
		task_name,
		status=None,
		result=None,
		error=None,
		traceback=None,
		output_path=None,
		scan_history_id=None,
		engine_id=None,
		subscan_id=None):
	task = ScanActivity.objects.filter(id=id)
	scan = task.first().scan_of
	scan_id = scan.id if scan else scan_history_id
	status_h = CELERY_TASK_STATUS_MAP.get(status) if status else None

	# Trim error before saving to DB
	if error and len(error) > 300:
		error = error[:288] + '...[trimmed]'

	if status:
		task.update(
			status=status,
			error_message=error,
			traceback=traceback,
			time=timezone.now())

	# Send notification
	from reNgine.tasks import send_task_status_notification
	send_task_status_notification.delay(
		task_name,
		status=status_h,
		result=result,
		traceback=traceback,
		output_path=output_path,
		scan_history_id=scan_id,
		engine_id=engine_id,
		subscan_id=subscan_id)

	return result


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
		output_path = f'{results_dir}/{filename}'

		if RENGINE_RECORD_ENABLED:
			if engine_id: # task not in engine.tasks, skip it.
				engine = EngineType.objects.get(pk=engine_id)
				if name not in engine.tasks:
					logger.debug(f'Task {name} is not part of engine "{engine.engine_name}" tasks. Skipping.')
					return

			# Create ScanActivity for this task and send start scan notifs
			logger.warning(f'Task {name} is RUNNING')
			activity_id = create_scan_activity(
				self.request.id,
				name,
				RUNNING_TASK,
				title=description,
				scan_history_id=scan_id,
				subscan_id=subscan_id,
				engine_id=engine_id)

		if RENGINE_CACHE_ENABLED:
			# Check for result in cache and return it if it's a hit
			record_key = get_task_cache_key(name, *args, **kwargs)
			result = cache.get(record_key)
			if result and result != b'null':
				if RENGINE_RECORD_ENABLED:
					logger.warning(f'Task {name} status is SUCCESS (CACHED)')
					update_scan_activity(
						activity_id,
						name,
						SUCCESS_TASK,
						result,
						output_path=output_path,
						engine_id=engine_id,
						scan_history_id=scan_id,
						subscan_id=subscan_id)

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
			result = traceback
			output_path = get_traceback_path(name, results_dir, scan_id, subscan_id)
			os.makedirs(os.path.dirname(output_path), exist_ok=True)

			if RENGINE_RAISE_ON_ERROR:
				raise exc

			logger.exception(exc)

		finally:
			status_str = CELERY_TASK_STATUS_MAP[status]

			if RENGINE_RECORD_ENABLED:
				# Update ScanActivity for this task: change task status, add 
				# error and traceback to db when the task failed, send scan
				# status notification.
				logger.warning(f'Task {self.name} status is {status_str}')
				update_scan_activity(
					activity_id,
					name,
					status,
					result=result,
					error=error,
					traceback=traceback,
					output_path=output_path,
					engine_id=engine_id,
					scan_history_id=scan_id,
					subscan_id=subscan_id)


		# Set task result in cache
		if RENGINE_CACHE_ENABLED and status == SUCCESS_TASK and result:
			cache.set(record_key, json.dumps(result))
			cache.expire(record_key, 600) # 10mn cache

		return result

	def s(self, *args, **kwargs):
		# TODO: set task status to INIT when creating a signature.
		return super().s(*args, **kwargs)
import json
import logging
import os
from sre_constants import SUCCESS
import traceback
from time import time

import django
from celery import Celery, Task
from celery.app.log import TaskFormatter
from celery.signals import after_setup_task_logger
from celery.utils.log import get_task_logger
from celery.worker.request import Request
from django.utils import timezone
from redis import Redis
from reNgine.definitions import (DYNAMIC_ID, FAILED_TASK, INITIATED_TASK, RUNNING_TASK,
                                 SUCCESS_TASK, CELERY_TASK_STATUS_MAP)
from reNgine.settings import (CELERY_RAISE_ON_ERROR, CELERY_TASK_CACHE,
                              CELERY_TASK_CACHE_IGNORE_KWARGS,
                              CELERY_TASK_SKIP_RECORD_ACTIVITY, DEBUG)

cache = Redis.from_url(os.environ['CELERY_BROKER'])
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reNgine.settings')

# db imports only work if django is loaded, so MUST be placed after django setup
django.setup()
from startScan.models import ScanActivity, ScanHistory
from scanEngine.models import EngineType

def create_scan_activity(scan_history_id, message, status):
	scan_activity = ScanActivity()
	scan_activity.scan_of = ScanHistory.objects.get(pk=scan_history_id)
	scan_activity.title = message
	scan_activity.time = timezone.now()
	scan_activity.status = status
	scan_activity.save()
	return scan_activity.id


def update_scan_activity(id, status, error=None):
    scan_activity = ScanActivity.objects.filter(id=id)
    if error and len(error) > 300:
        error = error[:288] + '...[trimmed]'
    return scan_activity.update(
			status=status,
			error_message=error,
			time=timezone.now())


class RengineRequest(Request):
    pass


class RengineTask(Task):
    Request = RengineRequest
    def __call__(self, *args, **kwargs):
        # Get task function name
        task_name = self.name.split('.')[-1]
        logger = get_task_logger(task_name)

        # Check if this task needs to be recorded.
        RECORD_TASK = self.name not in CELERY_TASK_SKIP_RECORD_ACTIVITY

        # If task is not in engine.tasks, skip it
        if RECORD_TASK and 'engine_id' in kwargs:
            engine = EngineType.objects.get(pk=kwargs['engine_id'])
            if task_name not in engine.tasks:
                logger.debug(f'{task_name} is not part of this engine tasks. Skipping.')
                return

        # Prepare task
        args_str = '_'.join([str(arg) for arg in args])
        kwargs_str = '_'.join([f'{k}={v}' for k, v in kwargs.items() if k not in CELERY_TASK_CACHE_IGNORE_KWARGS])
        task_descr = kwargs.pop('description', None) or ' '.join(task_name.split('_')).capitalize()
        task_result = None
        task_error = None
        task_descr += f' | {args_str} | {kwargs_str}' if DEBUG > 1 else ''
        scan_history_id = args[0] if len(args) > 0 else kwargs.get('scan_history_id')
        has_activity_id = (
            (len(args) > 1 and isinstance(args[1], int) and args[1] == DYNAMIC_ID)
            or
            kwargs.get('activity_id', DYNAMIC_ID) == DYNAMIC_ID
        )

        # Create scan activity only if we have a scan_history_id and 
        # activity_id in the task args
        RECORD_ACTIVITY =  scan_history_id and has_activity_id and RECORD_TASK
        if RECORD_ACTIVITY:
            activity_id = create_scan_activity(
                scan_history_id=scan_history_id,
                message=task_descr,
                status=INITIATED_TASK)
            # Set activity id as task arg
            if len(args) > 1:
                args = list(args)
                args[1] = activity_id
                args = tuple(args)
            elif 'activity_id' in kwargs:
                kwargs['activity_id'] = activity_id

        # Mark task as running
        task_status = RUNNING_TASK
        logger.warning(f'Task {self.name} status is RUNNING')
        if RECORD_ACTIVITY:
            update_scan_activity(activity_id, task_status)

        # Check for result in cache and return if hit
        if CELERY_TASK_CACHE:
            record_key = f'{self.name}__{args_str}__{kwargs_str}'
            task_result = cache.get(record_key)
            if task_result and task_result != b'null':
                if RECORD_ACTIVITY:
                    logger.warning(f'Task {self.name} status is SUCCESS (CACHED)')
                    update_scan_activity(activity_id, SUCCESS_TASK)
                return json.loads(task_result)

        # Execute task
        try:
            task_result = self.run(*args, **kwargs)
            task_status = SUCCESS_TASK
        except Exception as exc:
            task_status = FAILED_TASK
            task_error = repr(exc)
            tb = fmt_traceback(exc)
            task_error += f'\n => {tb}' if DEBUG > 0 else '' # append traceback to error
            logger.exception(exc)
            if CELERY_RAISE_ON_ERROR:
                raise exc
        finally:
            status = CELERY_TASK_STATUS_MAP[task_status]
            logger.warning(f'Task {self.name} status is {status}')
            if RECORD_ACTIVITY:
                update_scan_activity(activity_id, task_status, task_error)
                # TODO: send status notifs
                # notification = Notification.objects.first()
                # send_status = notification.send_scan_status_notif if notification else False
                # logger.info(msg)
                # if send_status:
                #   send_notification(msg)

        # Set task result in cache
        if CELERY_TASK_CACHE and task_status == SUCCESS_TASK and task_result:
            cache.set(record_key, json.dumps(task_result))
            cache.expire(record_key, 600) # 10mn cache

        return task_result

    def s(self, *args, **kwargs):
        # TODO: set task status to INIT when creating a signature.
        return super().s(*args, **kwargs)

def fmt_traceback(exc):
    return '\n'.join(traceback.format_exception(None, exc, exc.__traceback__))
    
# Celery app
app = Celery('reNgine', task_cls=RengineTask)
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

@after_setup_task_logger.connect
def setup_task_logger(logger, *args, **kwargs):
    for handler in logger.handlers:
        handler.setFormatter(TaskFormatter('%(task_name)s | %(message)s'))

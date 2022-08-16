import os
import json

from time import time

from celery import Celery, Task
from celery.worker.request import Request
from celery.signals import after_setup_task_logger, task_prerun, task_postrun
from celery.app.log import TaskFormatter

from redis import Redis
cache = Redis.from_url(os.environ['CELERY_BROKER'])

import logging

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reNgine.settings')

logger = logging.getLogger()

class RengineRequest(Request):
    pass
    # def on_timeout(self, soft, timeout):
    #     super(RengineRequest, self).on_timeout(soft, timeout)
    #     if not soft:
    #        logger.warning(
    #            'A hard timeout was enforced for task %s',
    #            self.task.name
    #        )

    # def on_failure(self, exc_info, send_failed_event=True, return_ok=False):
    #     super().on_failure(
    #         exc_info,
    #         send_failed_event=send_failed_event,
    #         return_ok=return_ok
    #     )
    #     logger.warning(
    #         'Failure detected for task %s',
    #         self.task.name
    #     )

IGNORE_KWARGS_CACHE = ['scan_history_id']
class RengineTask(Task):
    Request = RengineRequest
    def __call__(self, *args, **kwargs):
        args_str = '_'.join([str(arg) for arg in args])
        kwargs_str = '_'.join([f'{k}={v}' for k, v in kwargs.items() if k not in IGNORE_KWARGS_CACHE])
        record_key = f'{self.name}__{args_str}__{kwargs_str}'
        result = cache.get(record_key)
        if result:
            logger.info(f'Cache hit for {record_key}. Skipping task execution.')
            return json.loads(result)
        logger.info(f'Cache miss for {record_key}')
        result = self.run(*args, **kwargs)
        cache.set(record_key, json.dumps(result))
        cache.expire(record_key, 600) # 10mn cache
        return result

app = Celery('reNgine', task_cls=RengineTask)
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

d = {}

@task_prerun.connect
def task_prerun_handler(signal, sender, task_id, task, args, kwargs, **extras):
    d[task_id] = time()

@task_postrun.connect
def task_postrun_handler(signal, sender, task_id, task, args, kwargs, retval, state, **extras):
    try:
        cost = time() - d.pop(task_id)
    except KeyError:
        cost = -1
    print(f'{task.__name__}: finished in {cost}s')

@after_setup_task_logger.connect
def setup_task_logger(logger, *args, **kwargs):
    for handler in logger.handlers:
        handler.setFormatter(TaskFormatter('%(task_name)s - %(pathname)s - %(levelname)s - %(message)s'))

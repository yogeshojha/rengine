from __future__ import absolute_import
from reNgine import *

import time
import os
from celery import Celery
from celery import current_app
# `after_task_publish` is available in celery 3.1+
# for older versions use the deprecated `task_sent` signal
from celery.signals import after_task_publish




# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reNgine.settings')

#app = Celery('startScan')
app = Celery('server', broker='redis://127.0.0.1:6379/0')
# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()


@app.task()
def debug_task2(i,a):
    print(i+a)
    time.sleep(100.4)


@after_task_publish.connect
def update_sent_state(sender=None, headers=None, **kwargs):
    # the task may not exist if sent using `send_task` which
    # sends tasks by name, so fall back to the default result backend
    # if that is the case.
    task = current_app.tasks.get(sender)
    backend = task.backend if task else current_app.backend
    backend.store_result(headers['id'], None, "SENT")





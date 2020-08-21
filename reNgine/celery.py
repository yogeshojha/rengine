from __future__ import absolute_import
from reNgine import *

import time
import os
from celery import Celery
from reNgine.task import doScan



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

import os

import django
from celery import Celery
from celery.app import trace
from celery.app.log import TaskFormatter
from celery.signals import after_setup_task_logger

trace.LOG_SUCCESS = 'Task %(name)s[%(id)s] succeeded in %(runtime)ss'

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reNgine.settings')
django.setup()

# Celery app
app = Celery('reNgine')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

@after_setup_task_logger.connect
def setup_task_logger(logger, *args, **kwargs):
	for handler in logger.handlers:
		handler.setFormatter(TaskFormatter('%(task_name)s | %(message)s'))

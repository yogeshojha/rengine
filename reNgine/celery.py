import os
from celery import Celery


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reNgine.settings')

app = Celery('reNgine')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

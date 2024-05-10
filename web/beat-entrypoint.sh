#!/bin/bash

poetry run -C $HOME/ python3 manage.py collectstatic
poetry run -C $HOME/ python3 manage.py migrate

celery -A reNgine beat -l INFO --scheduler django_celery_beat.schedulers:DatabaseScheduler

exec "$@"

#!/bin/bash

loglevel='info'
if [ "$DEBUG" == "1" ]; then
    loglevel='debug'
fi

poetry run -C $HOME/ celery -A reNgine beat --loglevel=$loglevel --scheduler django_celery_beat.schedulers:DatabaseScheduler

exec "$@"
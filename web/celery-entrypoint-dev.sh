#!/bin/bash

if [ "$DEBUG" == "1" ]; then
    # Django debug toolbar
    pip install django-debug-toolbar
    export CELERY_LOGLEVEL='debug'
fi

# Check if remote debugging is enabled and set concurrency to 1 for easier debug
if [ "$REMOTE_DEBUG" == "1" ]; then
    # Live debug
    pip install debugpy

    # To debug opened port with netstat
    apt install net-tools -y

    # Set celery concurrency to 1 because thread processes is hard to debug
    export MIN_CONCURRENCY=1
    export MAX_CONCURRENCY=1
fi

./celery-entrypoint.sh
#!/bin/bash

# Django debug toolbar
pip install django-debug-toolbar

python3 manage.py migrate
python3 manage.py runserver 0.0.0.0:8000

exec "$@"

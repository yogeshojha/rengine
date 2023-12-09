#!/bin/bash

# Django debug toolbar
pip install django-debug-toolbar

python3 manage.py migrate

exec "$@"

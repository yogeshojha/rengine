#!/bin/bash

# Debug mode (uncomment to activate debug & display Django Debug Toolbar)
# /!\ Do not leave this activated when publicly exposed
#export DEBUG=1

# Django debug toolbar
pip install django-debug-toolbar

python3 manage.py migrate
python3 manage.py runserver 0.0.0.0:8000

exec "$@"

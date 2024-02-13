#!/bin/bash

# Debug mode (uncomment to activate debug & display Django Debug Toolbar)
# /!\ Do not leave this activated when publicly exposed
#export DEBUG=1

# Django debug toolbar
pip install django-debug-toolbar

./entrypoint.sh

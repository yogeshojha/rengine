#!/bin/sh


python manage.py migrate

# Load default engine types
python manage.py loaddata fixtures/default_scan_engines.json --app scanEngine.EngineType

# python manage.py collectstatic --no-input --clear

exec "$@"

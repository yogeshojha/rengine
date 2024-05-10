#!/bin/bash

poetry run -C $HOME/ python3 manage.py collectstatic --no-input
poetry run -C $HOME/ python3 manage.py migrate

poetry run -C $HOME/ python3 manage.py loaddata fixtures/default_scan_engines.yaml --app scanEngine.EngineType
poetry run -C $HOME/ python3 manage.py loaddata fixtures/default_keywords.yaml --app scanEngine.InterestingLookupModel
poetry run -C $HOME/ python3 manage.py loaddata fixtures/external_tools.yaml --app scanEngine.InstalledExternalTool

poetry run -C $HOME/ celery -A reNgine beat -l INFO --scheduler django_celery_beat.schedulers:DatabaseScheduler

exec "$@"

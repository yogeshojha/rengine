#!/bin/sh

if [ "$DATABASE" = "postgres" ]
then
    echo "Waiting for postgres..."

    while ! nc -z db 5432; do
      sleep 0.1
    done

    echo "PostgreSQL started"
fi

python manage.py migrate
python manage.py collectstatic --no-input --clear

# Load default engine types
python manage.py loaddata fixtures/default_scan_engines.yaml --app scanEngine.EngineType

exec "$@"

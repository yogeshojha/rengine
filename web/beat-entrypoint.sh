#!/bin/bash

if [ "$DATABASE" = "postgres" ]
then
    echo "Waiting for postgres..."

    while ! nc -z ${POSTGRES_HOST} ${POSTGRES_PORT}; do
      sleep 0.1
    done

    echo "PostgreSQL started"
fi

echo "Waiting for Celery to start"
while ! celery -A reNgine status; do
  sleep 0.5
done

python3 manage.py migrate

exec "$@"

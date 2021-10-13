#!/bin/bash

if [ "$DATABASE" = "postgres" ]
then
    echo "Waiting for postgres..."

    while ! nc -z db 5432; do
      sleep 0.1
    done

    echo "PostgreSQL started"
fi

echo "Waiting for Celery to start"
while ! celery -A reNgine status; do
  sleep 0.5
done

exec "$@"

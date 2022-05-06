#!/bin/bash

if [ "$DATABASE" = "postgres" ]
then
    echo "Waiting for postgres..."

    while ! nc -z ${POSTGRES_HOST} ${POSTGRES_PORT}; do
      sleep 0.1
    done

    echo "PostgreSQL started"
fi

python3 manage.py migrate

python3 manage.py runserver 0.0.0.0:8000

exec "$@"

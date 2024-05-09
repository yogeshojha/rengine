#!/bin/bash

poetry run -C $HOME/ python manage.py migrate

exec "$@"

@echo off

:: Credits: https://github.com/ninjhacks

set COMPOSE_ALL_FILES  = -f docker-compose.yml
set SERVICES           = db web proxy redis celery celery-beat

:: Generate certificates.
if "%1" == "certs" docker-compose -f docker-compose.setup.yml run --rm certs
:: Generate certificates.
if "%1" == "setup" docker-compose -f docker-compose.setup.yml run --rm certs
:: Build and start all services.
if "%1" == "up" docker-compose %COMPOSE_ALL_FILES% up -d --build %SERVICES%
:: Build all services.
if "%1" == "build" docker-compose %COMPOSE_ALL_FILES% build %SERVICES%
:: Generate Username (Use only after make up).
if "%1" == "username" docker-compose %COMPOSE_ALL_FILES% exec web python manage.py createsuperuser
:: Pull Docker images.
if "%1" == "pull" docker login docker.pkg.github.com & docker-compose %COMPOSE_ALL_FILES% pull
:: Down all services.
if "%1" == "down" docker-compose %COMPOSE_ALL_FILES% down
:: Stop all services.
if "%1" == "stop" docker-compose %COMPOSE_ALL_FILES% stop %SERVICES%
:: Restart all services.
if "%1" == "restart" docker-compose %COMPOSE_ALL_FILES% restart %SERVICES%
:: Remove all services containers.
if "%1" == "rm" docker-compose %COMPOSE_ALL_FILES% rm -f %SERVICES%
:: Tail all logs with -n 1000.
if "%1" == "logs" docker-compose %COMPOSE_ALL_FILES% logs --follow --tail=1000 %SERVICES%
:: Show all Docker images.
if "%1" == "images" docker-compose %COMPOSE_ALL_FILES% images %SERVICES%
:: Remove containers and delete volume data.
if "%1" == "prune" docker-compose %COMPOSE_ALL_FILES% stop %SERVICES% & docker-compose %COMPOSE_ALL_FILES% rm -f %SERVICES% & docker volume prune -f
:: Show this help.
if "%1" == "help" @echo Make application docker images and manage containers using docker-compose files only for windows.

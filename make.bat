@echo off

:: Credits: https://github.com/ninjhacks

set COMPOSE_ALL_FILES  = -f docker-compose.yml
set SERVICES           = db web proxy redis celery celery-beat ollama

:: Check if 'docker compose' command is available
docker compose version >nul 2>&1
if %errorlevel% == 0 (
    set DOCKER_COMPOSE=docker compose
) else (
    set DOCKER_COMPOSE=docker-compose
)


:: Generate certificates.
if "%1" == "certs" %DOCKER_COMPOSE% -f docker-compose.setup.yml run --rm certs
:: Generate certificates.
if "%1" == "setup" %DOCKER_COMPOSE% -f docker-compose.setup.yml run --rm certs
:: Build and start all services.
if "%1" == "up" %DOCKER_COMPOSE% %COMPOSE_ALL_FILES% up -d --build %SERVICES%
:: Build all services.
if "%1" == "build" %DOCKER_COMPOSE% %COMPOSE_ALL_FILES% build %SERVICES%
:: Generate Username (Use only after make up).
if "%1" == "username" %DOCKER_COMPOSE% %COMPOSE_ALL_FILES% exec web python3 manage.py createsuperuser
:: Apply migrations
if "%1" == "migrate" %DOCKER_COMPOSE% %COMPOSE_ALL_FILES% exec web python3 manage.py migrate
:: Pull Docker images.
if "%1" == "pull" %DOCKER_COMPOSE% docker.pkg.github.com & docker-compose %COMPOSE_ALL_FILES% pull
:: Down all services.
if "%1" == "down" %DOCKER_COMPOSE% %COMPOSE_ALL_FILES% down
:: Stop all services.
if "%1" == "stop" %DOCKER_COMPOSE% %COMPOSE_ALL_FILES% stop %SERVICES%
:: Restart all services.
if "%1" == "restart" %DOCKER_COMPOSE% %COMPOSE_ALL_FILES% restart %SERVICES%
:: Remove all services containers.
if "%1" == "rm" %DOCKER_COMPOSE% %COMPOSE_ALL_FILES% rm -f %SERVICES%
:: Tail all logs with -n 1000.
if "%1" == "logs" %DOCKER_COMPOSE% %COMPOSE_ALL_FILES% logs --follow --tail=1000 %SERVICES%
:: Show all Docker images.
if "%1" == "images" %DOCKER_COMPOSE% %COMPOSE_ALL_FILES% images %SERVICES%
:: Remove containers and delete volume data.
if "%1" == "prune" %DOCKER_COMPOSE% %COMPOSE_ALL_FILES% stop %SERVICES% & docker-compose %COMPOSE_ALL_FILES% rm -f %SERVICES% & docker volume prune -f
:: Show this help.
if "%1" == "help" @echo Make application Docker images and manage containers using Docker Compose files only for windows.

#!/bin/bash

cat ../web/art/reNgine.txt
echo "Uninstalling reNgine"

if [ "$EUID" -ne 0 ]
  then
  echo "Error uninstalling reNgine, Please run this script as root!"
  echo "Example: sudo ./uninstall.sh"
  exit
fi

read -p "This action will remove all containers, volumes and networks of reNgine. Do you want to continue? [y/n] " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]
then
  echo "Stopping reNgine"
  docker stop rengine-web-1 rengine-db-1 rengine-celery-1 rengine-celery-beat-1 rengine-redis-1 rengine-tor-1 rengine-proxy-1

  echo "Removing all containers related to reNgine"
  docker rm rengine-web-1 rengine-db-1 rengine-celery-1 rengine-celery-beat-1 rengine-redis-1 rengine-tor-1 rengine-proxy-1
  echo "Removed all containers"

  echo "Removing all volumes related to reNgine"
  docker volume rm rengine_gf_patterns rengine_github_repos rengine_nuclei_templates rengine_postgres_data rengine_scan_results rengine_tool_config
  echo "Removed all volumes"

  echo "Removing all networks related to reNgine"
  docker network rm rengine_rengine_network rengine_default
else
  exit 1
fi

read -p "Do you want to remove Docker images related to reNgine? [y/n] " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]
then
  echo "Removing all Docker images related to reNgine"
  docker rmi rengine_celery-beat rengine_celery docker.pkg.github.com/yogeshojha/rengine/rengine rengine_certs redis:alpine nginx:alpine peterdavehello/tor-socks-proxy postgres:12.3-alpine
  echo "Removed all Docker images"
else
  echo "Skipping removal of Docker images"
fi

read -p "Do you want to remove all Docker-related leftovers? [y/n] " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]
then
  echo "Removing all Docker-related leftovers"
  docker system prune -a -f
  echo "Removed all Docker-related leftovers"
else
  echo "Skipping removal of Docker-related leftovers"
fi

echo "Finished uninstalling."

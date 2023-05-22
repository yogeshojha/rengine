#!/bin/bash

cat ../web/art/reNgine.txt
echo "Uninstalling reNgine"

if [ "$EUID" -ne 0 ]
  then
  echo "Error uninstalling reNgine, Please run this script as root!"
  echo "Example: sudo ./uninstall.sh"
  exit
fi

echo "Stopping reNgine"
docker stop rengine_web_1 rengine_db_1 rengine_celery_1 rengine_celery-beat_1 rengine_redis_1 rengine_tor_1 rengine_proxy_1

echo "Removing all containers related to reNgine"
docker rm rengine_web_1 rengine_db_1 rengine_celery_1 rengine_celery-beat_1 rengine_redis_1 rengine_tor_1 rengine_proxy_1
echo "Removed all containers"

echo "Removing all volumes related to reNgine"
docker volume rm rengine_gf_patterns rengine_github_repos rengine_nuclei_templates rengine_postgres_data rengine_scan_results rengine_tool_config
echo "Removed all volumes"

echo "Removing all networks related to reNgine"
docker network rm rengine_rengine_network rengine_default

read -p "Do you want to remove Docker images related to reNgine? [y/n] " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]
then
  echo "Removing all Docker images related to reNgine"
  docker rmi rengine_celery_beat rengine_celery docker.pkg.github.com/yogeshojha/rengine/rengine rengine_certs redis nginx peterdavehello/tor_socks_proxy postgres
  echo "Removed all Docker images"
else
  echo "Skipping removal of Docker images"
fi

read -p "Do you want to remove all Docker builders? [y/n] " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]
then
  echo "Running docker builder prune -a command"
  docker builder prune -a
  echo "Removed all Docker builders"
else
  echo "Skipping removal of Docker builders"
fi

echo "Finished uninstalling."

#!/bin/bash

cat ../web/art/rengine.txt
echo "Uninstalling reNgine"

if [ "$EUID" -ne 0 ]
  then
  echo "Error uninstalling reNgine, Please run this script as root!"
  echo "Example: sudo ./uninstall.sh"
  exit
fi

echo "Stopping reNgine"
docker stop rengine_web_1 rengine_db_1 rengine_celery_1 rengine_celery-beat_1 rengine_redis_1 rengine_tor_1 rengine_proxy_1

echo "Removing all Containers related to reNgine"
docker rm rengine_web_1 rengine_db_1 rengine_celery_1 rengine_celery-beat_1 rengine_redis_1 rengine_tor_1 rengine_proxy_1
echo "Removed all Containers"

echo "Removing All volumes related to reNgine"
docker volume rm rengine_gf_patterns rengine_github_repos rengine_nuclei_templates rengine_postgres_data rengine_scan_results rengine_tool_config
echo "Removed all Volumes"

echo "Removing all networks related to reNgine"
docker network rm rengine_rengine_network

echo "Finished Uninstalling."

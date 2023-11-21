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

if [[ $REPLY =~ ^[Yy]$ ]]
then
  echo "Stopping reNgine"
  docker stop rengine-web-1 rengine-db-1 rengine-celery-1 rengine-celery-beat-1 rengine-redis-1 rengine-tor-1 rengine-proxy-1
  echo "Stopped reNgine"

  echo "Removing all containers related to reNgine"
  docker rm rengine-web-1 rengine-db-1 rengine-celery-1 rengine-celery-beat-1 rengine-redis-1 rengine-tor-1 rengine-proxy-1
  echo "Removed all containers related to reNgine"

  echo "Removing all volumes related to reNgine"
  docker volume rm rengine_gf_patterns rengine_github_repos rengine_nuclei_templates rengine_postgres_data rengine_scan_results rengine_tool_config rengine_static_volume rengine_wordlist
  echo "Removed all volumes related to reNgine"

  echo "Removing all networks related to reNgine"
  docker network rm rengine_rengine_network rengine_default
  echo "Removed all networks related to reNgine"
else
  exit 1
fi

echo "Finished Uninstalling."

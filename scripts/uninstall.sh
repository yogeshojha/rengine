#!/bin/bash

tput setaf 2;
cat ../web/art/reNgine.txt

tput setaf 3;
echo "Uninstalling reNgine, everything will be wiped!"
echo "Containers, images, volumes and network"

if [ "$EUID" -ne 0 ]
  then
  echo "Error uninstalling reNgine, Please run this script as root!"
  echo "Example: sudo ./uninstall.sh"
  exit
fi

tput setaf 1;
read -p 'Are you sure (y/n)?' -n 1 -r

if [[ $REPLY =~ ^[Yy]$ ]]
then
  echo ""
  tput setaf 3;
  echo "Stopping reNgine"
  tput setaf 4;
  docker stop rengine-web-1 rengine-db-1 rengine-celery-1 rengine-celery-beat-1 rengine-redis-1 rengine-proxy-1
  tput setaf 3;
  echo "Stopped reNgine"

  echo "Removing all containers related to reNgine"
  tput setaf 4;
  docker rm rengine-web-1 rengine-db-1 rengine-celery-1 rengine-celery-beat-1 rengine-redis-1 rengine-proxy-1
  tput setaf 3;
  echo "Removed all containers related to reNgine"

  echo "Removing all images related to reNgine"
  tput setaf 4;
  docker image rm rengine-celery rengine-celery-beat rengine-certs docker.pkg.github.com/yogeshojha/rengine/rengine nginx:alpine redis:alpine postgres:12.3-alpine
  tput setaf 3;
  echo "Removed all images related to reNgine"

  echo "Removing all volumes related to reNgine"
  tput setaf 4;
  docker volume rm rengine_gf_patterns rengine_github_repos rengine_nuclei_templates rengine_postgres_data rengine_scan_results rengine_tool_config rengine_static_volume rengine_wordlist
  tput setaf 3;
  echo "Removed all volumes related to reNgine"

  echo "Removing all networks related to reNgine"
  tput setaf 4;
  docker network rm rengine_rengine_network rengine_default
  tput setaf 3;
  echo "Removed all networks related to reNgine"
else
  tput setaf 2;
  echo ""
  echo "Exiting!"
  exit 1
fi

tput setaf 2;
echo "Finished Uninstalling."

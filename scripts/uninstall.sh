#!/bin/bash

tput setaf 2;
cat ../web/art/reNgine.txt

tput setaf 3;
echo ""
echo "Uninstalling reNGine"

if [ "$EUID" -ne 0 ]
  then
  echo ""
  echo "Error uninstalling reNGine, Please run this script as root!"
  echo "Example: sudo ./uninstall.sh"
  exit
fi

tput setaf 1;
echo ""
read -p "This action will stop and remove all containers, volumes and networks of reNGine. Do you want to continue? [y/n] " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]
then
  echo ""
  tput setaf 3;
  echo "Stopping reNGine"
  tput setaf 4;
  docker stop rengine-web-1 rengine-db-1 rengine-celery-1 rengine-celery-beat-1 rengine-redis-1 rengine-proxy-1
  tput setaf 3;
  echo "Stopped reNGine"
  echo ""

  echo "Removing all containers related to reNGine"
  tput setaf 4;
  docker rm rengine-web-1 rengine-db-1 rengine-celery-1 rengine-celery-beat-1 rengine-redis-1 rengine-proxy-1
  tput setaf 3;
  echo "Removed all containers related to reNGine"
  echo ""

  echo "Removing all volumes related to reNGine"
  tput setaf 4;
  docker volume rm rengine_gf_patterns rengine_github_repos rengine_nuclei_templates rengine_postgres_data rengine_scan_results rengine_tool_config rengine_static_volume rengine_wordlist
  tput setaf 3;
  echo "Removed all volumes related to reNGine"
  echo ""

  echo "Removing all networks related to reNGine"
  tput setaf 4;
  docker network rm rengine_rengine_network rengine_default
  tput setaf 3;
  echo "Removed all networks related to reNGine"
  echo ""
else
  tput setaf 2;
  echo ""
  echo "Exiting!"
  exit 1
fi

tput setaf 1;
read -p "Do you want to remove Docker images related to reNGine? [y/n] " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]
then
  echo ""
  tput setaf 3;
  echo "Removing all Docker images related to reNGine"
  tput setaf 4;
  docker image rm rengine-celery rengine-celery-beat rengine-certs docker.pkg.github.com/yogeshojha/rengine/rengine nginx:alpine redis:alpine postgres:12.3-alpine
  tput setaf 3;
  echo "Removed all Docker images"
  echo ""
else
  tput setaf 2;
  echo ""
  echo "Skipping removal of Docker images"
fi

tput setaf 1;
read -p "Do you want to remove all Docker-related leftovers? [y/n] " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]
then
  echo ""
  tput setaf 3;
  echo "Removing all Docker-related leftovers"
  tput setaf 4;
  docker system prune -a -f
  tput setaf 3;
  echo "Removed all Docker-related leftovers"
  echo ""
else
  echo ""
  echo "Skipping removal of Docker-related leftovers"
  echo ""
fi


tput setaf 2;
echo "Finished uninstalling."

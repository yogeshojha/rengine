#!/bin/bash

cat ../web/art/reNgine.txt
echo "Uninstalling reNgine"

if [ "$EUID" -ne 0 ]
  then
  echo -e "\e[31mError uninstalling reNgine, Please run this script as root!\e[0m"
  echo -e "\e[31mExample: sudo ./uninstall.sh\e[0m"
  exit
fi

DANGER='\e[31m'
SUCCESS='\e[32m'
WARNING='\e[33m'
INFO='\e[34m'
RESET='\e[0m'

print_status() {
    echo -e "${INFO}--------------------------------------------------${RESET}"
    echo -e "${INFO}$1${RESET}"
    echo -e "${INFO}--------------------------------------------------${RESET}"
}

print_status "WARNING: You are about to uninstall rengine"
echo -e "${DANGER}This action is not reversible. All containers, volumes, networks, and scan results will be removed.${RESET}"
echo -e "${DANGER}There is no going back after this point.${RESET}"
read -p "$(echo -e ${WARNING}"Are you sure you want to proceed? (y/Y/yes/YES to confirm): "${RESET})" -r CONFIRM

# change answer to lowecase for comparison
ANSWER_LC=$(echo "$CONFIRM" | tr '[:upper:]' '[:lower:]')

if [ -z "$CONFIRM" ] || { [ "$CONFIRM" != "y" ] && [ "$CONFIRM" != "Y" ] && [ "$CONFIRM" != "yes" ] && [ "$CONFIRM" != "Yes" ] && [ "$CONFIRM" != "YES" ]; }; then
    print_status "${WARNING}Uninstall aborted by user.${RESET}"
    exit 0
fi

print_status "${INFO}Proceeding with uninstalling reNgine${RESET}"

print_status "Stopping all containers related to reNgine..."
docker stop $(docker ps -a -q --filter name=rengine) 2>/dev/null

print_status "Removing all containers related to reNgine..."
docker rm $(docker ps -a -q --filter name=rengine) 2>/dev/null

print_status "Removing all volumes related to reNgine..."
docker volume rm $(docker volume ls -q --filter name=rengine) 2>/dev/null

print_status "Removing all networks related to reNgine..."
docker network rm $(docker network ls -q --filter name=rengine) 2>/dev/null

print_status "Removing all images related to reNgine..."
docker rmi $(docker images -q --filter reference=rengine) 2>/dev/null

print_status "Performing final cleanup"
docker system prune -f --volumes --filter "label=com.docker.compose.project=rengine"

print_status "${SUCCESS}reNgine uninstall process has been completed.${RESET}"

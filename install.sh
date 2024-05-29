#!/bin/bash

#log messages in different colors
log() {
  tput setaf "$2"
  printf "$1\r\n"
  tput sgr0  # Reset text color
}

# Check for root privileges
if [ "$(id -u)" -ne 0 ]; then
  log "Error: Please run this script as root!" 1
  log "Example: sudo $0" 1
  exit 1
fi

usageFunction()
{
  log "Usage: $0 (-n) (-h)" 2
  log "\t-n Non-interactive installation (Optional)" 2
  log "\t-h Show usage" 2
  exit 1
}

tput setaf 2;
cat web/art/reNgine.txt

log "\r\nBefore running this script, please make sure Docker is running and you have made changes to the `.env` file." 1
log "Changing the postgres username & password from .env is highly recommended.\r\n" 1

log "#########################################################################" 4
log "Please note that this installation script is only intended for Linux" 3
log "Only x86_64 platform are supported" 3
log "#########################################################################\r\n" 4

tput setaf 1;

isNonInteractive=false
while getopts nh opt; do
   case $opt in
      n) isNonInteractive=true ;;
      h) usageFunction ;;
      ?) usageFunction ;;
   esac
done

if [ $isNonInteractive = false ]; then
  read -p 'Are you sure you made changes to the `.env` file (y/n)? ' answer
  case ${answer:0:1} in
      y|Y|yes|YES|Yes )
        log "Continuing Installation!" 2
      ;;
      * )
        if [ -x "$(command -v nano)" ]; then
          log "nano already installed, skipping." 2
        else
          sudo apt update && sudo apt install nano -y
          log "nano installed!" 2
        fi
      nano .env
      ;;
  esac
else
  log "Non-interactive installation parameter set. Installation begins." 4
fi

log "\r\nInstalling reNgine and its dependencies" 4
log "=========================================================================" 4

log "\r\n#########################################################################" 4
log "Installing curl..." 4

if ! command -v curl 2> /dev/null; then
  apt update && apt install curl -y
  log "CURL installed!" 2
else
  log "CURL already installed, skipping." 2
fi


log "\r\n#########################################################################" 4
log "Installing Docker..." 4

if ! command -v docker 2> /dev/null; then
  curl -fsSL https://get.docker.com -o get-docker.sh && sh get-docker.sh
  log "Docker installed!" 2
else
  log "Docker already installed, skipping." 2
fi

log "\r\n#########################################################################" 4
log "Installing docker-compose" 4

if ! command -v docker-compose 2> /dev/null; then
  curl -L "https://github.com/docker/compose/releases/download/v2.5.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
  chmod +x /usr/local/bin/docker-compose
  ln -s /usr/local/bin/docker-compose /usr/bin/docker-compose
  log "docker-compose installed!" 2
else
  log "docker-compose already installed, skipping." 2
fi

log "\r\n#########################################################################" 4
log "Installing make" 4

if ! command -v make 2> /dev/null; then
  apt install make -y
  log "make installed!" 2
else
  log "make already installed, skipping." 2
fi

log "\r\n#########################################################################" 4
log "Checking Docker status" 4
if docker info >/dev/null 2>&1; then
  log "Docker is running." 2
else
  log "Docker is not running. Please run docker and try again." 1
  log "You can run Docker service using: sudo systemctl start docker" 1
  exit 1
fi



log "\r\n#########################################################################" 4
log "Installing reNgine, please be patient it could take a while" 4

log "\r\n=========================================================================" 5
log "Generating certificates and building docker images" 5
log "=========================================================================" 5
make certs && make build && log "reNgine is built" 2 || { log "reNgine installation failed!!" 1; exit 1; }

log "\r\n=========================================================================" 5
log "Docker containers starting, please wait celery container could be long" 5
log "=========================================================================" 5
make up && log "reNgine is installed!" 2 || { log "reNgine installation failed!!" 1; exit 1; }


log "\r\n#########################################################################" 4
log "Creating an account" 4
log "#########################################################################" 4
  make username isNonInteractive=$isNonInteractive
  make migrate

log "In case you have unapplied migrations (see above in red), run 'make migrate'" 2
log "\r\nThank you for installing reNgine, happy recon!!" 2

#!/bin/bash
 
#log messages in different colors
log() {
  tput setaf "$2"
  echo "$1"
  tput sgr0  # Reset text color
}
 
# Check for root privileges
if [ "$(id -u)" -ne 0 ]; then
  log "Error: Please run this script as root!" 1
  log "Example: sudo $0" 1
  exit 1
fi
 
log "#########################################################################" 4
log "Please note that this installation script is only intended for Linux" 3
log "For Mac and Windows, refer to the official guide https://rengine.wiki" 3
log "#########################################################################" 4
 
log "Installing reNgine and its dependencies" 4
 
log "#########################################################################" 4
log "Installing curl..." 4
 
if ! command -v curl &> /dev/null; then
  apt update && apt install curl -y
  log "CURL installed!!!" 2
else
  log "CURL already installed, skipping." 2
fi
 
log "#########################################################################" 4
log "Installing Docker..." 4
 
if ! command -v docker &> /dev/null; then
  curl -fsSL https://get.docker.com -o get-docker.sh && sh get-docker.sh
  log "Docker installed!!!" 2
else
  log "Docker already installed, skipping." 2
fi
 
log "#########################################################################" 4
log "Installing docker-compose" 4
 
if ! command -v docker-compose &> /dev/null; then
  curl -L "https://github.com/docker/compose/releases/download/v2.5.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
  chmod +x /usr/local/bin/docker-compose
  ln -s /usr/local/bin/docker-compose /usr/bin/docker-compose
  log "docker-compose installed!!!" 2
else
  log "docker-compose already installed, skipping." 2
fi
 
log "#########################################################################" 4
log "Installing make" 4
 
if ! command -v make &> /dev/null; then
  apt install make -y
  log "make installed!!!" 2
else
  log "make already installed, skipping." 2
fi
 
log "#########################################################################" 4
log "Checking Docker status" 4
 
if docker info >/dev/null 2>&1; then
  log "Docker is running." 4
else
  log "Docker is not running. Please run docker and try again." 1
  log "You can run Docker service using: sudo systemctl start docker" 1
  exit 1
fi
 
log "#########################################################################" 4
log "Installing reNgine" 4
 
make certs && make build && make up && log "reNgine is installed!!!" 2 || { log "reNgine installation failed!!" 1; exit 1; }
 
log "#########################################################################" 4
log "Creating an account" 4
 
make username
 
log "Thank you for installing reNgine, happy recon!!" 2
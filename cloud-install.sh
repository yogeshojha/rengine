#!/bin/bash

print_and_log() {
	echo "$1" | sudo tee /var/log/reNgine.log
}
print_and_log "Installing reNgine and it's dependencies"

print_and_log " "
if [ "$EUID" -ne 0 ]; then
	print_and_log "Error installing reNgine, Please run this script as root!" | tee -a /var/log/reNgine.log
	print_and_log "Example: sudo ./cloud-install.sh"
	exit
fi

print_and_log " "
print_and_log "#########################################################################"
print_and_log "Installing curl..."
print_and_log "#########################################################################"
if [ -x "$(command -v curl)" ]; then
	print_and_log "CURL already installed, skipping."
else
	sudo apt update && sudo apt install curl -y
	print_and_log "CURL installed!!!"
fi

print_and_log " "
print_and_log "#########################################################################"
print_and_log "Installing Docker..."
print_and_log "#########################################################################"
if [ -x "$(command -v docker)" ]; then
	print_and_log "Docker already installed, skipping."
else
	curl -fsSL https://get.docker.com -o get-docker.sh && sh get-docker.sh
	print_and_log "Docker installed!!!"
fi

print_and_log " "
print_and_log "#########################################################################"
print_and_log "Installing docker-compose"
print_and_log "#########################################################################"
if [ -x "$(command -v docker-compose)" ]; then
	print_and_log "docker-compose already installed, skipping."
else
	curl -L "https://github.com/docker/compose/releases/download/v2.23.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
	chmod +x /usr/local/bin/docker-compose
	ln -s /usr/local/bin/docker-compose /usr/bin/docker-compose
	print_and_log "docker-compose installed!!!"
fi

print_and_log " "
print_and_log "#########################################################################"
print_and_log "Installing make"
print_and_log "#########################################################################"
if [ -x "$(command -v make)" ]; then
	print_and_log "make already installed, skipping."
else
	apt install make
fi

print_and_log " "
print_and_log "#########################################################################"
print_and_log "Checking Docker status"
print_and_log "#########################################################################"
if docker info >/dev/null 2>&1; then
	print_and_log "Docker is running."
else
	print_and_log "Docker is not running. Please run docker and try again."
	print_and_log "You can run docker service using sudo systemctl start docker"
	exit 1
fi

print_and_log " "
print_and_log "#########################################################################"
print_and_log "Installing reNgine"
print_and_log "#########################################################################"
make certs && make cloud_build && make cloud_up && print_and_log "reNgine is installed!!!" && failed=0 || failed=1

if [ "${failed}" -eq 0 ]; then
	sleep 3

	print_and_log " "
	print_and_log "#########################################################################"
	print_and_log "Creating an account"
	print_and_log "#########################################################################"
	make cloud_username
fi

#!/usr/bin/env bash

# Display usage
usage_function() {
  echo " "
  tput setaf 2
  echo "Usage: $0 [-n] [-h]"
  echo -e "\t-n Non-interactive installation (Optional)"
  echo -e "\t-h Show usage"
  exit 1
}

# Print success messages
success_message() {
  tput setaf 2
  echo "$1"
}

# Print error messages
error_message() {
  tput setaf 1
  echo "$1"
}

# Print informational messages
info_message() {
  tput setaf 4
  echo "$1"
}

# Check and install packages
install_package() {
  local package=$1
  local install_command=$2
  if [ -x "$(command -v $package)" ]; then
    success_message "$package already installed, skipping."
  else
    info_message "Installing $package..."
    eval $install_command
    success_message "$package installed!"
  fi
}

# Function to check Docker status
check_docker_status() {
  if docker info >/dev/null 2>&1; then
    success_message "Docker is running."
  else
    error_message "Docker is not running. Please start Docker and try again."
    error_message "You can start Docker using: sudo systemctl start docker"
    exit 1
  fi
}

# Display initial information
info_message "$(cat web/art/reNgine.txt)"
error_message "Before running this script, please make sure Docker is running and you have updated the .env file."
success_message "Changing the postgres username & password from .env is highly recommended."

# Parse command-line options
is_non_interactive=false
while getopts "nh" opt; do
  case $opt in
    n) is_non_interactive=true ;;
    h) usage_function ;;
    ?) usage_function ;;
  esac
done

# Confirm .env file changes if not in non-interactive mode
if [ "$is_non_interactive" = false ]; then
  read -p "Are you sure you have made changes to the .env file (y/n)? " answer
  case ${answer:0:1} in
    y|Y|yes|YES|Yes )
      success_message "Continuing Installation!"
      ;;
    * )
      nano .env
      ;;
  esac
else
  success_message "Non-interactive installation parameter set. Installation begins."
fi

# Display general installation information
info_message "############################################################################################"
info_message "This installation script is intended for Debian (based) Linux distros only."
info_message "For Mac and Windows, refer to the official guide: https://rengine.wiki"
info_message "############################################################################################"

# Check for root privileges
if [ "$EUID" -ne 0 ]; then
  error_message "Error: This script must be run as root!"
  error_message "Example: sudo ./install.sh"
  exit 1
fi

# Install necessary packages
install_package "curl" "sudo apt update && sudo apt install curl -y"
install_package "docker" "curl -fsSL https://get.docker.com -o get-docker.sh && sh get-docker.sh"
install_package "docker-compose" "curl -L \"https://github.com/docker/compose/releases/download/v2.5.0/docker-compose-$(uname -s)-$(uname -m)\" -o /usr/local/bin/docker-compose && chmod +x /usr/local/bin/docker-compose && ln -s /usr/local/bin/docker-compose /usr/bin/docker-compose"
install_package "make" "apt install make -y"

# Check Docker status
check_docker_status

# Install reNgine
info_message "#########################################################################"
info_message "Installing reNgine"
info_message "#########################################################################"
make certs && make build && make up
if [ $? -eq 0 ]; then
  success_message "reNgine is installed!"
  sleep 3
  info_message "#########################################################################"
  info_message "Creating an account"
  info_message "#########################################################################"
  if [ "$is_non_interactive" = true ]; then
    make username isNonInteractive=true
  else
    make username
  fi
  make migrate
  success_message "Thank you for installing reNgine, happy recon!"
  echo "In case you have unapplied migrations, run 'make migrate'"
else
  error_message "reNgine installation failed!"
fi

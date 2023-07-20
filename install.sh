#!/bin/bash

# Check if terminal supports color output
if ! tput setaf 1 &>/dev/null; then
  color_support=false
else
  color_support=true
fi

# Function to print colored output
print_color() {
  local color="$1"
  local message="$2"
  if $color_support; then
    tput setaf "$color"
  fi
  echo "$message"
  if $color_support; then
    tput sgr0
  fi
}

# Check if Docker is running
if ! systemctl is-active docker &>/dev/null; then
  print_color 1 "Docker is not running. Please run Docker and try again."
  print_color 1 "You can run Docker service using 'sudo systemctl start docker'"
  exit 1
fi

# Prompt user to edit .env file or continue with installation
print_color 2 "Before running this script, please make sure Docker is running and you have made changes to .env file."
print_color 2 "Changing the Postgres username & password from .env is highly recommended."
read -p "Are you sure, you made changes to .env file (y/n)? " answer
case "${answer:0:1}" in
    y|Y)
      print_color 2 "Continuing Installation!"
    ;;
    *)
      # Check if nano is available before using it
      if ! command -v nano &>/dev/null; then
        print_color 1 "nano is not installed. Please edit .env manually."
        exit 1
      fi
      nano .env
    ;;
esac

print_color 3 "#########################################################################"
print_color 3 "Please note that, this installation script is only intended for Linux"
print_color 3 "For Mac and Windows, refer to the official guide https://rengine.wiki"
print_color 3 "#########################################################################"

# Check if the script is running with root privileges
if [ "$EUID" -ne 0 ]; then
  print_color 1 "Error installing reNgine, Please run this script as root!"
  print_color 1 "Example: sudo ./install.sh"
  exit 1
fi

# Function to install a package if not already installed
install_package() {
  local package="$1"
  if ! command -v "$package" &>/dev/null; then
    if [ -x "$(command -v apt)" ]; then
      apt update && apt install "$package" -y
    else
      print_color 1 "Package manager not supported. Please install $package manually."
      exit 1
    fi
  fi
}

# Install required packages
print_color 4 "#########################################################################"
print_color 4 "Installing curl..."
print_color 4 "#########################################################################"
install_package curl

print_color 4 "#########################################################################"
print_color 4 "Installing Docker..."
print_color 4 "#########################################################################"
if ! command -v docker &>/dev/null; then
  print_color 1 "Docker is not installed. Please install Docker manually."
  exit 1
fi

print_color 4 "#########################################################################"
print_color 4 "Installing docker-compose"
print_color 4 "#########################################################################"
install_package docker-compose

print_color 4 "#########################################################################"
print_color 4 "Installing make"
print_color 4 "#########################################################################"
install_package make

print_color 4 "#########################################################################"
print_color 4 "Checking Docker status"
print_color 4 "#########################################################################"

# Verify Docker installation success
if command -v docker &>/dev/null && systemctl is-active docker &>/dev/null; then
  print_color 4 "Docker is running."
else
  print_color 1 "Docker is not running. Please run Docker and try again."
  print_color 1 "You can run Docker service using 'sudo systemctl start docker'"
  exit 1
fi

print_color 4 "#########################################################################"
print_color 4 "Installing reNgine"
print_color 4 "#########################################################################"

# Add error handling for reNgine installation
if ! make certs && make build && make up; then
  print_color 1 "Error installing reNgine. Please check the logs for more information."
  exit 1
fi

print_color 2 "reNgine is installed!!!"

sleep 3

print_color 4 "#########################################################################"
print_color 4 "Creating an account"
print_color 4 "#########################################################################"

# Add error handling for make username command
if ! make username; then
  print_color 1 "Error creating an account. Please check the logs for more information."
  exit 1
fi

print_color 2 "Thank you for installing reNgine, happy recon!!"

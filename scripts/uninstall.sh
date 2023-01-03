#!/bin/bash

# Print the contents of rengine.txt
cat ../web/art/rengine.txt

# Print a message indicating that the uninstallation process is starting
echo "Uninstalling reNgine"

# Check if the script is being run as root
if [ "$EUID" -ne 0 ]
then
  # If not, print an error message and exit
  echo "Error: Please run this script as root!"
  echo "Example: sudo ./uninstall.sh"
  exit
fi

# Print a message indicating that reNgine is being stopped
echo "Stopping reNgine"

# Stop all Docker containers related to reNgine
docker stop rengine_web_1 rengine_db_1 rengine_celery_1 rengine_celery-beat_1 rengine_redis_1 rengine_tor_1 rengine_proxy_1

# Print a message indicating that the reNgine containers are being removed
echo "Removing all Containers related to reNgine"

# Remove all Docker containers related to reNgine
if docker rm rengine_web_1 rengine_db_1 rengine_celery_1 rengine_celery-beat_1 rengine_redis_1 rengine_tor_1 rengine_proxy_1; then
  # Print a message indicating that the containers have been removed
  echo "Removed all Containers"
else
  # If any of the containers are missing, print an error message
  echo "Error: One or more Containers were not found. Skipping removal of Containers."
fi

# Print a message indicating that the reNgine volumes are being removed
echo "Removing All volumes related to reNgine"

# Remove all Docker volumes related to reNgine
if docker volume rm rengine_gf_patterns rengine_github_repos rengine_nuclei_templates rengine_postgres_data rengine_scan_results rengine_tool_config; then
  # Print a message indicating that the volumes have been removed
  echo "Removed all Volumes"
else
  # If any of the volumes are missing, print an error message
  echo "Error: One or more Volumes were not found. Skipping removal of Volumes."
fi

# Print a message indicating that the reNgine network is being removed
echo "Removing all networks related to reNgine"

# Remove the Docker network used by reNgine
if docker network rm rengine_rengine_network; then
  # Print a message indicating that the network has been removed
  echo "Removed reNgine network"
else
  # If the network is missing, print an error message
  echo "Error: reNgine network was not found. Skipping removal of network."
fi

# Print a message indicating that the uninstallation process is complete
echo "Finished Uninstalling."

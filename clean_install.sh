#!/bin/bash

# This shell script deletes all Docker data such as containers, networks, images and volumes. In case executing this script doesn't work, allow it to execute: `sudo chmod +x ./clean_start.sh`

echo "Done pruning; all resources have been removed."
docker system prune -a -f --volumes

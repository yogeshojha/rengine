#!/bin/sh

# run subdomain takeover check
subjack -w $1/sorted_subdomain_collection.txt -o $1/takeover_result.json --ssl -c /app/tools/subjack_fingerprint.json -v

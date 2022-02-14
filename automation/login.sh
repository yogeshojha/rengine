#!/bin/bash

echo "INFO: Getting CSRF token ..."
curl -s "$1/login/" -c cookiejar --insecure -o /dev/null && \
csrf=$(cat cookiejar | grep csrftoken | rev | cut -d$'\t' -f1 | rev) && \
echo "DEBUG: csrftoken=$csrf" && \
echo "INFO: Logging in ..." && \
curl -s -d "username=$2&password=$3&csrfmiddlewaretoken=$csrf" "$1/login/" -X POST -b cookiejar -c cookiejar --insecure && \
sessionid=$(cat cookiejar | grep sessionid | rev | cut -d$'\t' -f1 | rev) && \
echo "INFO: Got sessionid"
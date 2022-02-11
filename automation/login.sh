#!/bin/bash

curl "$1/login/" -c cookiejar --insecure -o /dev/null && \
csrf=$(cat cookiejar | grep csrftoken | rev | cut -d$'\t' -f1 | rev) && \
echo "csrftoken=$csrf" && \
curl -d "username=$2&password=$3&csrfmiddlewaretoken=$csrf" "$1/login/" -X POST -b cookiejar -c cookiejar --insecure --proxy http://localhost:8080 && \
sessionid=$(cat cookiejar | grep sessionid | rev | cut -d$'\t' -f1 | rev) && \
echo "sessionid=$sessionid"
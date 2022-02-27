#!/bin/bash

if [ ! $# -eq 4 ]; then
    echo "Usage: $0 <rengine_url> <rengine_username> <rengine_password> <org_name>"
    exit 1
fi

bash login.sh $1 $2 $3

echo "INFO: Getting CSRF token ..."
csrf=$(curl -s $1/target/add/organization -b cookiejar -c cookiejar --insecure | sed -n "s/^.*name=\"csrfmiddlewaretoken\" value=\"\(.*\)\".*$/\1/p")

echo "INFO: Creating Organization ..."
curl -vv $1/target/add/organization -b cookiejar --insecure -o /dev/null -d "csrfmiddlewaretoken=$csrf&name=$4&descrption=created via automation from Hackerone" --proxy http://localhost:8080

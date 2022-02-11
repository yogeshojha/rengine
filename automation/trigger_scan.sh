#!/bin/bash

if [ ! $# -eq 5 ]; then
    echo "Usage: $0 <rengine_url> <target_domain> <rengine_username> <rengine_password> <scan_engine_id>"
    exit 1
fi

bash login.sh $1 $3 $4

targets=""
get_targets () {
    targets=$(curl -b cookiejar "$1/api/queryTargetsWithoutOrganization/" --insecure)
}

get_target_id () {
    target_id=$(echo $targets | jq ".domains[] | if (.name == \"$1\") then .id else empty end")
}

trigger () {
    echo "Getting CSRF token ..."
    csrf=$(curl $1/scan/start/$2 -b cookiejar -c cookiejar | sed -n "s/^.*name=\"csrfmiddlewaretoken\" value=\"\(.*\)\".*$/\1/p")
    echo "csrf=$csrf"

    echo "Triggering scan ..."
    included_subdomains_file=included_subdomains.txt
    touch $included_subdomains_file
    curl $1/scan/start/$2 -b cookiejar -d "csrfmiddlewaretoken=$csrf&scan_mode=$3&importSubdomainTextArea=$(cat $included_subdomains_file)&outOfScopeSubdomainTextarea="

}

get_targets $1
echo $targets
get_target_id $2
echo $target_id
trigger $1 $target_id $5
rm cookiejar

#!/bin/bash

if [ ! $# -eq 6 ]; then
    echo "Usage: $0 <rengine_url> <target_domain> <rengine_username> <rengine_password> <scan_engine> <included_subdomains_file>"
    exit 1
fi

bash login.sh $1 $3 $4

targets=""
get_targets () {
    targets=$(curl -s -b cookiejar "$1/api/queryTargetsWithoutOrganization/" --insecure)
}

get_target_id () {
    target_id=$(echo $targets | jq ".domains[] | if (.name == \"$1\") then .id else empty end")
}

get_engine_id () {
    echo "INFO: Looking for engine $2"
    engine_id=$(curl -s -b cookiejar "$1/api/listEngines/" --insecure | jq ".engines[] | if (.engine_name==\"$2\") then .id else empty end")
}

trigger () {
    echo "INFO: Getting CSRF token ..."
    csrf=$(curl -s $1/scan/start/$2 -b cookiejar -c cookiejar --insecure | sed -n "s/^.*name=\"csrfmiddlewaretoken\" value=\"\(.*\)\".*$/\1/p")
    # echo "csrf=$csrf"

    echo "INFO: Triggering scan ..."
    included_subdomains_file=$4
    touch $included_subdomains_file
    curl -s $1/scan/start/$2 -b cookiejar --insecure -o /dev/null -d "csrfmiddlewaretoken=$csrf&scan_mode=$3&importSubdomainTextArea=$(cat $included_subdomains_file)&outOfScopeSubdomainTextarea="

}

get_targets $1
get_target_id $2
echo "DEBUG: Target ID: $target_id"

get_engine_id $1 "$5"
echo "DEBUG: Engine ID: $engine_id"

trigger $1 $target_id $engine_id $6
rm cookiejar

echo "INFO: Done"

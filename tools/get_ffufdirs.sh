#!/bin/sh

if [[ $# -eq 5 ]]
then
python3 /app/tools/dirsearch/dirsearch.py -u $1 -w $2 --json-report=$3 -e $4 -t $5 -e $4
else
ffuf -u $1/FUZZ -w $2 -ac -ic -sf -H "X-Forwarded-For: 127.0.0.1" -H "X-BugBounty: BadRequests" -H "User-Agent: Mozilla/5.0 (X11; Linux x86_64; rv:72.0) Gecko/20100101 Firefox/72.0" -o $3
fi

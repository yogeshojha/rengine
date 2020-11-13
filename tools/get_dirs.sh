#!/bin/sh

if [[ $# -eq 5 ]]
then
python3 /app/tools/dirsearch/dirsearch.py -u $1 -w $2 --json-report=$3 -e $4 -t $5 -e $4 --exclude-texts=Attack Detected,Please contact the system administrator,the page you were trying to view does not exist
else
python3 /app/tools/dirsearch/dirsearch.py -u $1 -w $2 --json-report=$3 -e $4 -t $5 -r -R $6 -e $4 --exclude-texts=Attack Detected,Please contact the system administrator,the page you were trying to view does not exist
fi

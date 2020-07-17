#!/bin/sh

# rm -rf $2

if [[ $# -eq 4 ]]
then
python3 /app/tools/dirsearch/dirsearch.py -w /app/tools/dirsearch/db/dicc.txt -u $1 --json-report=$2 -t $3 -e $4 --suff $4
else
python3 /app/tools/dirsearch/dirsearch.py -w /app/tools/dirsearch/db/dicc.txt -u $1 --json-report=$2 -t $3 -e $4 --suff $4 -r -R $5
fi

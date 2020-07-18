#!/bin/sh

if [[ $# -eq 4 ]]
then
python3 /app/tools/dirsearch/dirsearch.py -w $1 -u $2 --json-report=$3 -t $4 -e $5 --suff $6
else
python3 /app/tools/dirsearch/dirsearch.py -w $1 -u $2 --json-report=$3 -t $4 -e $5 --suff $6 -r -R $7
fi

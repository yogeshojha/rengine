# $1 = subdomain
# usage $2 = domain_name scan result path

rm -rf $2
python3 /app/tools/dirsearch/dirsearch.py /app/tools/dirsearch/db/dicc.txt -u $1 --json-report=$2 -e *

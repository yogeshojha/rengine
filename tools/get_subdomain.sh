#!/bin/sh

python3 /app/tools/Sublist3r/sublist3r.py -d $1 -t 10 -o $2/from_sublister.txt
/app/tools/amass enum --passive -d $1 -o $2/fromamass.txt
assetfinder --subs-only $1 > $2/fromassetfinder.txt
subfinder -d $1 > $2/fromsubfinder.txt
cat $2/*.txt > $2/subdomain_collection.txt
rm -rf $2/from*
sort -u $2/subdomain_collection.txt -o $2/sorted_subdomain_collection.txt

rm -rf $2/subdomain*

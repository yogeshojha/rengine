#!/bin/sh

for i in "$@" ; do
    if [[ $i == "sublist3r" ]] ; then
        python3 /app/tools/Sublist3r/sublist3r.py -d $2 -t $1 -o $3/from_sublister.txt
    fi
    if [[ $i == "amass" ]] ; then
        /app/tools/amass enum --passive -d $2 -o $3/fromamass.txt
    fi
    if [[ $i == "assetfinder" ]] ; then
        assetfinder --subs-only $2 > $3/fromassetfinder.txt
    fi
    if [[ $i == "subfinder" ]] ; then
        subfinder -d $2 -t $1 > $3/fromsubfinder.txt
    fi
done

cat $3/*.txt > $3/subdomain_collection.txt
rm -rf $3/from*
sort -u $3/subdomain_collection.txt -o $3/sorted_subdomain_collection.txt

rm -rf $3/subdomain*

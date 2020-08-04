#!/bin/sh


# $1 threads, $2 domain, $3 output directory, $4 github_subdomains_token, $5 amass active recon wordlist, $6 amass_config


for i in "$@" ; do
    if [[ $i == "sublist3r" ]] ; then
        python3 /app/tools/Sublist3r/sublist3r.py -d $2 -t $1 -o $3/from_sublister.txt
    fi
    if [[ $i == "amass-passive" || $i == "amass" ]] ; then
        /app/tools/amass enum --passive -d $2 -o $3/fromamass.txt
    fi
    if [[ $i == "amass-active" ]] ; then
        /app/tools/amass enum -active -o $3/fromamass-active.txt -d $2 -brute -w $5 -config $6
    fi
    if [[ $i == "assetfinder" ]] ; then
        assetfinder --subs-only $2 > $3/fromassetfinder.txt
    fi
    if [[ $i == "subfinder" ]] ; then
        subfinder -d $2 -t $1 > $3/fromsubfinder.txt
    fi
    if [[ $i == "github-subdomains" ]] ; then
        python3 /app/tools/github-subdomains.py -d $2 -t $4 > $3/fromgithub.txt
    fi
done

cat $3/*.txt > $3/subdomain_collection.txt
rm -rf $3/from*
sort -u $3/subdomain_collection.txt -o $3/sorted_subdomain_collection.txt

rm -rf $3/subdomain*

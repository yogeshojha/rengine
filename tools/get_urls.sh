#!/bin/sh

while read subdomain; do
    echo "$subdomain" | gau -providers wayback | httpx -status-code -content-length -title -json -o $1/urls_wayback.json
    cat $1/urls_wayback.json >> $1/all_urls.json
    echo "$subdomain" | hakrawler -plain | httpx -status-code -content-length -title -json -o $1/urls_hakrawler.json >> $1/all_urls.json
    cat $1/urls_hakrawler.json >> $1/all_urls.json
done <$1/sorted_subdomain_collection.txt

rm -rf $1/urls*

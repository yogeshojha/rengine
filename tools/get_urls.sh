#!/bin/sh

echo $1 | gau -providers wayback | httpx -status-code -content-length -title -json -o $2/urls_wayback.json

echo $1 | hakrawler -plain | httpx -status-code -content-length -title -json -o $2/urls_hakrawler.json

cat $2/urls* > $2/all_urls.json

rm -rf $2/urls*

#!/bin/sh


for i in "$@" ; do
    if [[ $i == "gau" ]] ; then
        echo $1 | gau -providers wayback -o $2/urls_gau.txt
        httpx -l $2/urls_gau.txt -status-code -content-length -title -json -o $2/httpx_wayback.json
    fi
    if [[ $i == "hakrawler" ]] ; then
        hakrawler -plain -url $1 > $2/urls_hakrawler.txt
        httpx -l $2/urls_hakrawler.txt -status-code -content-length -title -json -o $2/httpx_hakrawler.json
    fi
done

cat $2/httpx* > $2/final_httpx_urls.json

cat $2/url* >> $2/all_urls.txt

# Sort and unique the endpoints
sort -u $2/all_urls.txt -o $2/all_urls.txt

# unfurl the urls to keep only domain and path
cat $2/all_urls.txt | unfurl -u format %s://%d%p >> $2/unfurl_urls.txt
sort -u $2/unfurl_urls.txt -o $2/unfurl_urls.txt

rm -rf $2/url*
rm -rf $2/httpx*

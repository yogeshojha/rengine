#!/bin/sh

for i in "$@" ; do
	while read domain; do
		domain=$(echo $domain | sed 's~http[s]*://~~g')
		if [[ $i == "gau" ]] ; then
        	echo $domain | gau -providers wayback | httpx -status-code -content-length -title -json -o $2/urls_wayback_$domain.json
	    fi
	    if [[ $i == "hakrawler" ]] ; then
	        echo $domain | hakrawler -plain | httpx -status-code -content-length -title -json -o $2/urls_hakrawler_$domain.json
	    fi
	    if [[ $i == "paramspider" ]] ; then
	        python3 /app/tools/ParamSpider/paramspider.py --domain $domain --subs False --exclude woff,css,js,png,svg,jpg | gf xss | sed 's/FUZZ$/XSS/g;'| httpx -status-code -content-length -title -json -o $2/urls_paramspider_gfXSS_$domain.json
					python3 /app/tools/ParamSpider/paramspider.py --domain $domain --subs False --exclude woff,css,js,png,svg,jpg | gf ssrf | sed 's/FUZZ$/SSRF/g;'| httpx -status-code -content-length -title -json -o $2/urls_paramspider_gfSSRF_$domain.json
					python3 /app/tools/ParamSpider/paramspider.py --domain $domain --subs False --exclude woff,css,js,png,svg,jpg | gf redirect | sed 's/FUZZ$/REDIRECT/g;'| httpx -status-code -content-length -title -json -o $2/urls_paramspider_gfREDIRECT_$domain.json
					python3 /app/tools/ParamSpider/paramspider.py --domain $domain --subs False --exclude woff,css,js,png,svg,jpg | gf sqli | sed 's/FUZZ$/SQLI/g;'| httpx -status-code -content-length -title -json -o $2/urls_paramspider_gfSQLI_$domain.json
					python3 /app/tools/ParamSpider/paramspider.py --domain $domain --subs False --exclude woff,css,js,png,svg,jpg | gf rce | sed 's/FUZZ$/RCE/g;'| httpx -status-code -content-length -title -json -o $2/urls_paramspider_gfRCE_$domain.json
					python3 /app/tools/ParamSpider/paramspider.py --domain $domain --subs False --exclude woff,css,js,png,svg,jpg | gf lfi | sed 's/FUZZ$/LFI/g;'| httpx -status-code -content-length -title -json -o $2/urls_paramspider_gfLFI_$domain.json
			fi
	done < $1
done

cat $2/urls* > $2/all_urls.json

rm -rf $2/urls*

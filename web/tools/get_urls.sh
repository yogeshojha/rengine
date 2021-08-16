#!/bin/bash

if [[ $3 == "deep" ]] ; then
  for i in "$@" ; do
      if [[ $i == "gauplus" ]] ; then
        echo "Running gauplus"
        cat $2/sorted_subdomain_collection.txt | gauplus --random-agent | grep -Eo $4 > $2/urls_gau.txt
      fi
      if [[ $i == "hakrawler" ]] ; then
        echo "Running hakrawler"
        cat $2/alive.txt | hakrawler | grep -Eo $4 > $2/urls_hakrawler.txt
      fi
      if [[ $i == "waybackurls" ]] ; then
        echo "Running waybackurls"
        cat $2/sorted_subdomain_collection.txt | waybackurls | grep -Eo $4 > $2/urls_wayback.txt
      fi
      if [[ $i == "gospider" ]] ; then
        echo "Running gospider"
        gospider -S $2/alive.txt -d 2 --sitemap --robots --js | grep -Eo $4 > $2/urls_gospider.txt
      fi
  done
else
  for i in "$@" ; do
      if [[ $i == "gauplus" ]] ; then
        echo "Running gauplus"
        echo $1 | gauplus --random-agent | grep -Eo $4 > $2/urls_gau.txt
      fi
      if [[ $i == "hakrawler" ]] ; then
        echo "Running hakrawler"
        hakrawler -plain -url $1 | grep -Eo $4 > $2/urls_hakrawler.txt
      fi
      if [[ $i == "waybackurls" ]] ; then
        echo "Running waybackurls"
        echo $1 | waybackurls | grep -Eo $4 > $2/urls_wayback.txt
      fi
      if [[ $i == "gospider" ]] ; then
        echo "Running gospider"
        gospider -s "https://"$2/alive.txt --sitemap --robots --js | grep -Eo $4 > $2/urls_gospider.txt
      fi
  done
fi

echo "Finished gathering urls, now sorting and running http probing"

cat $2/urls* > $2/final_urls.txt

# remove all urls*
rm -rf $2/url*

# Sort and unique the endpoints
cat $2/alive.txt >> $2/final_urls.txt
sort -u $2/final_urls.txt -o $2/all_urls.txt

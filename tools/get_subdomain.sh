python3 /app/tools/Sublist3r/sublist3r.py -d $1 -t 10 -o $2/from_sublister.txt
# /app/tools/amass enum --passive -d $1 -o $2/fromamass.txt
# /app/tools/assetfinder --subs-only $1 > $2/fromassetfinder.txt
cat $2/*.txt > $2/subdomain_collection.txt
rm -rf $2/from*
sort -u $2/subdomain_collection.txt -o $2/sorted_subdomain_collection.txt
rm -rf $2/subdomain*


# debug purpose
# cp /app/tools/scan_results/hackerone.com__2020_05_26_20_22_08/sorted_subdomain_collection.txt $2/sorted_subdomain_collection.txt
# cp /app/tools/scan_results/hackerone.com__2020_05_26_20_36_18/ports.json $2/ports.json
# cp /app/tools/scan_results/hackerone.com__2020_05_26_20_36_18/alive.txt $2/alive.txt


/app/tools/naabu -hL $2/sorted_subdomain_collection.txt -t 5 -oJ -o $2/ports.json

# check aliveness
for i in $(cat $2/sorted_subdomain_collection.txt); do echo "http://$i" && echo "https://$i"; done >> $2/with_protocol_domains.txt
cat $2/sorted_subdomain_collection.txt | /app/tools/httprobe | tee -a $2/alive.txt

#!/bin/bash

sudo -v &>/dev/null
tput setaf 2;
echo "Bulk Domains Insertion"

domain_file=$1
nb_domain_to_insert=$(wc -l $domain_file | awk '{print $1}')

tput setaf 6; echo "Found $nb_domain_to_insert domain(s) in $domain_file !"

timestamp=$(date +%s)
data_fname=/imports/domain_insertion_$timestamp.csv
ldata_fname=./db$data_fname
log_fname=/imports/domain_insertion_$timestamp.log
bad_fname=/imports/domain_insertion_$timestamp.bad
dup_fname=/imports/domain_insertion_$timestamp.dup

echo " "
tput setaf 4; echo "Quering last domain ID inserted ..."

last_domain_id=$(sudo docker-compose exec db psql -t -U rengine -d rengine -c 'select max(id) from public.targetapp_domain;' | awk 'NF==1 {print $1}')
if [ -z "$last_domain_id" ]
then
  last_domain_id=0
fi

tput setaf 2; echo "Last domain ID inserted = $last_domain_id"

echo " "
tput setaf 4; echo "Generating pg_bulkload data file at '$ldata_fname'..."

insert_date=$(date)
touch $ldata_fname
for domain in $(cat $domain_file)
do
    ((last_domain_id=last_domain_id+1))
    ldomain="${domain,,}"
    echo "$last_domain_id,$ldomain,,,,$insert_date,," | tee -a $ldata_fname >/dev/null
done

echo " "
tput setaf 4; echo "Creating pg_bulkload log files ..."
touch ./db$log_fname && chmod o+w ./db$log_fname
touch ./db$bad_fname && chmod o+w ./db$bad_fname
touch ./db$dup_fname && chmod o+w ./db$dup_fname

echo " "
tput setaf 4; echo "Creating pg_bulkload extension ..."
sudo docker-compose exec db psql -U rengine -d rengine -c "CREATE EXTENSION pg_bulkload" &2>/dev/null

echo " "
tput setaf 4; echo "Start insertion using pg_bulkload ..."
sudo docker-compose exec db touch /imports/test.{log,prs,dup}
sudo docker-compose exec db chmod o+w /imports/test.{log,prs,dup}
sudo docker-compose exec db pg_bulkload \
            --infile=$data_fname \
            --output=public.targetapp_domain \
            --option="WRITER=PARALLEL" \
            --option="TYPE=CSV" \
            --option="DELIMITER=," \
            --option="DUPLICATE_ERRORS=-1" \
            --option="PARSE_ERRORS=-1" \
            --option="ON_DUPLICATE_KEEP=OLD" \
            --option="CHECK_CONSTRAINTS=YES" \
            -U rengine \
            -d rengine \
            --logfile=$log_fname \
            --parse-badfile=$bad_fname \
            --duplicate-badfile=$dup_fname

echo " "
tput setaf 4; echo "Result log file available at './db$log_fname'"
tput setaf 4; echo "Bad records that cannot be parsed correctly available at './db$bad_fname'"
tput setaf 4; echo "Bad records that conflict with unique constraints available at './db$dup_fname'"
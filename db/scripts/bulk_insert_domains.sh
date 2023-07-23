#!/bin/bash

sudo -v &>/dev/null

domain_file=$1
organization=$2
web_server=https://localhost
engine_type=1

tput setaf 2;
echo "Bulk Domains Insertion"
nb_domain_to_insert=$(wc -l $domain_file | awk '{print $1}')

tput setaf 6; echo "Found $nb_domain_to_insert domain(s) in $domain_file !"

echo " "
tput setaf 4; echo "Quering last domain ID inserted ..."

last_domain_id=$(sudo docker-compose exec db psql -t -U rengine -d rengine -c 'select max(id) from public.targetapp_domain;' | awk 'NF==1 {print $1}')
if [ -z "$last_domain_id" ]
then
  last_domain_id=0
fi
tmp_domain_id=$last_domain_id

tput setaf 2; echo "Last domain ID inserted = $last_domain_id"

timestamp=$(date +%s)
data_fname=/imports/domain_insertion_$timestamp.csv
ldata_fname=./db$data_fname
log_fname=/imports/domain_insertion_$timestamp.log
bad_fname=/imports/domain_insertion_$timestamp.bad
dup_fname=/imports/domain_insertion_$timestamp.dup

echo " "
tput setaf 4; echo "Generating domain data file at '$ldata_fname'..."

insert_date=$(date)
touch $ldata_fname
for domain in $(cat $domain_file)
do
    ((last_domain_id=last_domain_id+1))
    ldomain="${domain,,}"
    echo "$last_domain_id,$ldomain,,,,$insert_date,$insert_date," | tee -a $ldata_fname >/dev/null
done

echo " "
tput setaf 4; echo "Creating pg_bulkload log files ..."
touch ./db$log_fname && chmod o+w ./db$log_fname
touch ./db$bad_fname && chmod o+w ./db$bad_fname
touch ./db$dup_fname && chmod o+w ./db$dup_fname

echo " "
tput setaf 4; echo "Creating pg_bulkload extension ..."
sudo docker-compose exec db psql -U rengine -d rengine -c "CREATE EXTENSION pg_bulkload" 2>/dev/null

echo " "
tput setaf 4; echo "Start domain instertion using pg_bulkload ..."; tput setaf 6;
sudo docker-compose exec db pg_bulkload \
            --infile=$data_fname \
            --output=public.targetapp_domain \
            --option="WRITER=PARALLEL" \
            --option="TYPE=CSV" \
            --option="DELIMITER=," \
            --option="DUPLICATE_ERRORS=-1" \
            --option="PARSE_ERRORS=-1" \
            --option="ON_DUPLICATE_KEEP=NEW" \
            --option="CHECK_CONSTRAINTS=YES" \
            -U rengine \
            -d rengine \
            --logfile=$log_fname \
            --parse-badfile=$bad_fname \
            --duplicate-badfile=$dup_fname

echo " "
tput setaf 5; echo "Result log file available at './db$log_fname'"
tput setaf 5; echo "Bad records that cannot be parsed correctly available at './db$bad_fname'"
tput setaf 5; echo "Bad records that conflict with unique constraints available at './db$dup_fname'"

echo " "
tput setaf 4; echo "Creating organization '$organization'..."
organization_id=$(sudo docker-compose exec db psql -t -U rengine -d rengine -c "insert into public.targetapp_organization(name, insert_date) values('$organization', now()) on conflict (name) do update set id=public.targetapp_organization.id, description=excluded.description returning id;" | awk 'NF==1 {print $1}')

tput setaf 6; echo "$organization created with ID = $organization_id !"


end_domain_id=$(sudo docker-compose exec db psql -t -U rengine -d rengine -c 'select max(id) from public.targetapp_domain;' | awk 'NF==1 {print $1}')
if [ $end_domain_id -eq $tmp_domain_id ]
then
  tput setaf 1; echo "No new domain imported, exiting ..."
  exit
fi

echo " "
tput setaf 4; echo "Quering last Organization <-> Domain relation id inserted ..."

last_relation_id=$(sudo docker-compose exec db psql -t -U rengine -d rengine -c "select max(id) from public.targetapp_organization_domains;" | awk 'NF==1 {print $1}')
if [ -z "$last_relation_id" ]
then
  last_relation_id=0
fi

tput setaf 2; echo "Last Organization <-> Domain relation id inserted = $last_relation_id"

timestamp=$(date +%s)
data_fname=/imports/relation_insertion_$timestamp.csv
ldata_fname=./db$data_fname
log_fname=/imports/relation_insertion_$timestamp.log
bad_fname=/imports/relation_insertion_$timestamp.bad
dup_fname=/imports/relation_insertion_$timestamp.dup

echo " "
tput setaf 4; echo "Generating relation data file at '$ldata_fname'..."

touch $ldata_fname
last_domain_id=$(($tmp_domain_id+1))
for domain_id in $(seq $last_domain_id $end_domain_id)
do
    ((last_relation_id=last_relation_id+1))
    echo "$last_relation_id,$organization_id,$domain_id" | tee -a $ldata_fname >/dev/null
done

echo " "
tput setaf 4; echo "Creating pg_bulkload log files ..."
touch ./db$log_fname && chmod o+w ./db$log_fname
touch ./db$bad_fname && chmod o+w ./db$bad_fname
touch ./db$dup_fname && chmod o+w ./db$dup_fname

echo " "
tput setaf 4; echo "Start relation insertion using pg_bulkload ..."; tput setaf 6;
sudo docker-compose exec db pg_bulkload \
            --infile=$data_fname \
            --output=public.targetapp_organization_domains \
            --option="WRITER=PARALLEL" \
            --option="TYPE=CSV" \
            --option="DELIMITER=," \
            --option="DUPLICATE_ERRORS=-1" \
            --option="PARSE_ERRORS=-1" \
            --option="ON_DUPLICATE_KEEP=NEW" \
            --option="CHECK_CONSTRAINTS=YES" \
            -U rengine \
            -d rengine \
            --logfile=$log_fname \
            --parse-badfile=$bad_fname \
            --duplicate-badfile=$dup_fname

echo " "
tput setaf 5; echo "Result log file available at './db$log_fname'"
tput setaf 5; echo "Bad records that cannot be parsed correctly available at './db$bad_fname'"
tput setaf 5; echo "Bad records that conflict with unique constraints available at './db$dup_fname'"


echo " "
tput setaf 4; echo "Quering last scan history id inserted ..."

last_scanhistory_id=$(sudo docker-compose exec db psql -t -U rengine -d rengine -c "select max(id) from public.startscan_scanhistory;" | awk 'NF==1 {print $1}')
if [ -z "$last_scanhistory_id" ]
then
  last_scanhistory_id=0
fi
tmp_scanhistory_id=$last_scanhistory_id

tput setaf 2; echo "Last scan history id inserted = $last_scanhistory_id"

timestamp=$(date +%s)
data_fname=/imports/scanhistory_insertion_$timestamp.csv
ldata_fname=./db$data_fname
log_fname=/imports/scanhistory_insertion_$timestamp.log
bad_fname=/imports/scanhistory_insertion_$timestamp.bad
dup_fname=/imports/scanhistory_insertion_$timestamp.dup

echo " "
tput setaf 4; echo "Generating scan history data file at '$ldata_fname'..."

touch $ldata_fname
last_domain_id=$(($tmp_domain_id+1))
for domain_id in $(seq $last_domain_id $end_domain_id)
do
    ((last_scanhistory_id=last_scanhistory_id+1))
    echo "$last_scanhistory_id,$insert_date,-1,'','',False,False,False,False,False,False,True,,True,$domain_id,$engine_type,," | tee -a $ldata_fname >/dev/null
done

echo " "
tput setaf 4; echo "Creating pg_bulkload log files ..."
touch ./db$log_fname && chmod o+w ./db$log_fname
touch ./db$bad_fname && chmod o+w ./db$bad_fname
touch ./db$dup_fname && chmod o+w ./db$dup_fname

echo " "
tput setaf 4; echo "Start scan history insertion using pg_bulkload ..."; tput setaf 6;
sudo docker-compose exec db pg_bulkload \
            --infile=$data_fname \
            --output=public.startscan_scanhistory \
            --option="WRITER=PARALLEL" \
            --option="TYPE=CSV" \
            --option="DELIMITER=," \
            --option="DUPLICATE_ERRORS=-1" \
            --option="PARSE_ERRORS=-1" \
            --option="ON_DUPLICATE_KEEP=NEW" \
            --option="CHECK_CONSTRAINTS=YES" \
            -U rengine \
            -d rengine \
            --logfile=$log_fname \
            --parse-badfile=$bad_fname \
            --duplicate-badfile=$dup_fname

echo " "
tput setaf 5; echo "Result log file available at './db$log_fname'"
tput setaf 5; echo "Bad records that cannot be parsed correctly available at './db$bad_fname'"
tput setaf 5; echo "Bad records that conflict with unique constraints available at './db$dup_fname'"

echo " "
tput setaf 4; echo "Start scaning tasks ..."

timestamp=$(date +%s)
data_fname=/imports/scanhistory_update_$timestamp.csv
ldata_fname=./db$data_fname
log_fname=/imports/scanhistory_update_$timestamp.log
bad_fname=/imports/scanhistory_update_$timestamp.bad
dup_fname=/imports/scanhistory_update_$timestamp.dup

echo " "
tput setaf 4; echo "Generating scan history data file at '$ldata_fname'..."

touch $ldata_fname
last_domain_id=$(($tmp_domain_id+1))
last_scanhistory_id=$tmp_scanhistory_id
for domain_id in $(seq $last_domain_id $end_domain_id)
do
    ((last_scanhistory_id=last_scanhistory_id+1))
    tput setaf 4; echo "Starting scan on domain id = $domain_id ..."
    celery_id=$(sudo docker-compose exec celery celery -A reNgine -b redis://redis:6379/0 --result-backend redis://redis:6379/0 call reNgine.tasks.initiate_scan -a ["$domain_id","$last_scanhistory_id",0,"$engine_type"])
    echo "$last_scanhistory_id,$insert_date,-1,'',$celery_id,False,False,False,False,False,False,True,,True,$domain_id,$engine_type,," | tee -a $ldata_fname >/dev/null
done

echo " "
tput setaf 4; echo "Creating pg_bulkload log files ..."
touch ./db$log_fname && chmod o+w ./db$log_fname
touch ./db$bad_fname && chmod o+w ./db$bad_fname
touch ./db$dup_fname && chmod o+w ./db$dup_fname

echo " "
tput setaf 4; echo "Updating scan history using pg_bulkload ..."; tput setaf 6;
sudo docker-compose exec db pg_bulkload \
            --infile=$data_fname \
            --output=public.startscan_scanhistory \
            --option="WRITER=PARALLEL" \
            --option="TYPE=CSV" \
            --option="DELIMITER=," \
            --option="DUPLICATE_ERRORS=-1" \
            --option="PARSE_ERRORS=-1" \
            --option="ON_DUPLICATE_KEEP=NEW" \
            --option="CHECK_CONSTRAINTS=YES" \
            -U rengine \
            -d rengine \
            --logfile=$log_fname \
            --parse-badfile=$bad_fname \
            --duplicate-badfile=$dup_fname

echo " "
tput setaf 5; echo "Result log file available at './db$log_fname'"
tput setaf 5; echo "Bad records that cannot be parsed correctly available at './db$bad_fname'"
tput setaf 5; echo "Bad records that conflict with unique constraints available at './db$dup_fname'"
#!/bin/bash

sudo -v &>/dev/null

domain_file=$1
organization=$2

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
start_domain_id=$last_domain_id

tput setaf 2; echo "Last domain ID inserted = $last_domain_id"

timestamp=$(date +%s)
data_fname=/imports/domain_insertion_$timestamp.csv
ldata_fname=./db$data_fname
log_fname=/imports/domain_insertion_$timestamp.log
bad_fname=/imports/domain_insertion_$timestamp.bad
dup_fname=/imports/domain_insertion_$timestamp.dup

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
sudo docker-compose exec db psql -U rengine -d rengine -c "CREATE EXTENSION pg_bulkload" 2>/dev/null

echo " "
tput setaf 4; echo "Start insertion using pg_bulkload ..."; tput setaf 6;
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
if [ $end_domain_id -lt $start_domain_id ]
then
  tput setaf 1; echo "Nothing to do, exiting ..."
  exit
fi

echo " "
tput setaf 4; echo "Quering last relation $organization / domain ID inserted ..."

last_relation_id=$(sudo docker-compose exec db psql -t -U rengine -d rengine -c "select max(id) from public.targetapp_organization_domains where organization_id = $organization_id;" | awk 'NF==1 {print $1}')
if [ -z "$last_relation_id" ]
then
  last_relation_id=0
fi

tput setaf 2; echo "Last relation $organization / domain ID inserted = $last_relation_id"

timestamp=$(date +%s)
data_fname=/imports/relation_insertion_$timestamp.csv
ldata_fname=./db$data_fname
log_fname=/imports/relation_insertion_$timestamp.log
bad_fname=/imports/relation_insertion_$timestamp.bad
dup_fname=/imports/relation_insertion_$timestamp.dup

echo " "
tput setaf 4; echo "Generating pg_bulkload data file at '$ldata_fname'..."

insert_date=$(date)
touch $ldata_fname
((start_domain_id=start_domain_id+1))
for i in $(seq $start_domain_id $end_domain_id)
do
    ((last_relation_id=last_relation_id+1))
    echo "$last_relation_id,$organization_id,$i" | tee -a $ldata_fname >/dev/null
done

echo " "
tput setaf 4; echo "Creating pg_bulkload log files ..."
touch ./db$log_fname && chmod o+w ./db$log_fname
touch ./db$bad_fname && chmod o+w ./db$bad_fname
touch ./db$dup_fname && chmod o+w ./db$dup_fname

echo " "
tput setaf 4; echo "Start insertion using pg_bulkload ..."; tput setaf 6;
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

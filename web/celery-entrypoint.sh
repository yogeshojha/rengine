#!/bin/bash

python3 manage.py makemigrations
python3 manage.py migrate
python3 manage.py collectstatic --no-input --clear

# Load default engines, keywords, and external tools
python3 manage.py loaddata fixtures/default_scan_engines.yaml --app scanEngine.EngineType
python3 manage.py loaddata fixtures/default_keywords.yaml --app scanEngine.InterestingLookupModel
python3 manage.py loaddata fixtures/external_tools.yaml --app scanEngine.InstalledExternalTool

# update whatportis
yes | whatportis --update

# clone dirsearch default wordlist
if [ ! -d "/usr/src/wordlist" ]
then
  echo "Making Wordlist directory"
  mkdir /usr/src/wordlist
fi

if [ ! -f "/usr/src/wordlist/" ]
then
  echo "Downloading Default Directory Bruteforce Wordlist"
  wget https://raw.githubusercontent.com/maurosoria/dirsearch/master/db/dicc.txt -O /usr/src/wordlist/dicc.txt
fi

# check if default wordlist for amass exists
if [ ! -f /usr/src/wordlist/deepmagic.com-prefixes-top50000.txt ];
then
  echo "Downloading Deepmagic top 50000 Wordlist"
  wget https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/DNS/deepmagic.com-prefixes-top50000.txt -O /usr/src/wordlist/deepmagic.com-prefixes-top50000.txt
fi

# clone Sublist3r
if [ ! -d "/usr/src/github/Sublist3r" ]
then
  echo "Cloning Sublist3r"
  git clone https://github.com/aboul3la/Sublist3r /usr/src/github/Sublist3r
fi
python3 -m pip install -r /usr/src/github/Sublist3r/requirements.txt

# clone OneForAll
if [ ! -d "/usr/src/github/OneForAll" ]
then
  echo "Cloning OneForAll"
  git clone https://github.com/shmilylty/OneForAll /usr/src/github/OneForAll
fi
python3 -m pip install -r /usr/src/github/OneForAll/requirements.txt

# clone eyewitness
if [ ! -d "/usr/src/github/EyeWitness" ]
then
  echo "Cloning EyeWitness"
  git clone https://github.com/FortyNorthSecurity/EyeWitness /usr/src/github/EyeWitness
  # pip install -r /usr/src/github/Eyewitness/requirements.txt
fi

# clone theHarvester
if [ ! -d "/usr/src/github/theHarvester" ]
then
  echo "Cloning theHarvester"
  git clone https://github.com/laramies/theHarvester /usr/src/github/theHarvester
fi
python3 -m pip install -r /usr/src/github/theHarvester/requirements/base.txt

# install h8mail
python3 -m pip install h8mail

# install gf patterns
if [ ! -d "/root/Gf-Patterns" ];
then
  echo "Installing GF Patterns"
  mkdir ~/.gf
  cp -r $GOPATH/src/github.com/tomnomnom/gf/examples/*.json ~/.gf
  git clone https://github.com/1ndianl33t/Gf-Patterns ~/Gf-Patterns
  mv ~/Gf-Patterns/*.json ~/.gf
fi

# store scan_results
if [ ! -d "/usr/src/scan_results" ]
then
  mkdir /usr/src/scan_results
fi

# test tools, required for configuration
naabu && subfinder && amass
nuclei

if [ ! -d "/root/nuclei-templates/geeknik_nuclei_templates" ];
then
  echo "Installing Geeknik Nuclei templates"
  git clone https://github.com/geeknik/the-nuclei-templates.git ~/nuclei-templates/geeknik_nuclei_templates
else
  echo "Removing old Geeknik Nuclei templates and updating new one"
  rm -rf ~/nuclei-templates/geeknik_nuclei_templates
  git clone https://github.com/geeknik/the-nuclei-templates.git ~/nuclei-templates/geeknik_nuclei_templates
fi

if [ ! -f ~/nuclei-templates/ssrf_nagli.yaml ];
then
  echo "Downloading ssrf_nagli for Nuclei"
  wget https://raw.githubusercontent.com/NagliNagli/BountyTricks/main/ssrf.yaml -O ~/nuclei-templates/ssrf_nagli.yaml
fi

if [ ! -d "/usr/src/github/CMSeeK" ]
then
  echo "Cloning CMSeeK"
  git clone https://github.com/Tuhinshubhra/CMSeeK /usr/src/github/CMSeeK
  pip install -r /usr/src/github/CMSeeK/requirements.txt
fi

if [ ! -d "/usr/src/github/Infoga" ]
then
  echo "Cloning Infoga"
  git clone https://github.com/m4ll0k/Infoga /usr/src/github/Infoga
fi

# clone ctfr
if [ ! -d "/usr/src/github/ctfr" ]
then
  echo "Cloning CTFR"
  git clone https://github.com/UnaPibaGeek/ctfr /usr/src/github/ctfr
fi

exec "$@"

# httpx seems to have issue, use alias instead!!!
echo 'alias httpx="/go/bin/httpx"' >> ~/.bashrc


echo "Starting Workers..."
watchmedo auto-restart --recursive --pattern="*.py" --directory="/usr/src/app/reNgine/" -- celery -A reNgine worker --concurrency=100 --pool=gevent --loglevel=info -Q initiate_scan_queue -n initiate_scan_worker &
watchmedo auto-restart --recursive --pattern="*.py" --directory="/usr/src/app/reNgine/" -- celery -A reNgine worker --concurrency=500 --pool=gevent --loglevel=info -Q subscan_queue -n subscan_worker &
watchmedo auto-restart --recursive --pattern="*.py" --directory="/usr/src/app/reNgine/" -- celery -A reNgine worker --concurrency=50 --pool=gevent --loglevel=info -Q report_queue -n report_worker &
watchmedo auto-restart --recursive --pattern="*.py" --directory="/usr/src/app/reNgine/" -- celery -A reNgine worker --concurrency=100 --pool=gevent --loglevel=info -Q subdomain_discovery_queue -n subdomain_discovery_worker &
watchmedo auto-restart --recursive --pattern="*.py" --directory="/usr/src/app/reNgine/" -- celery -A reNgine worker --concurrency=50 --pool=gevent --loglevel=info -Q osint_queue -n osint_worker &
watchmedo auto-restart --recursive --pattern="*.py" --directory="/usr/src/app/reNgine/" -- celery -A reNgine worker --concurrency=50 --pool=gevent --loglevel=info -Q osint_discovery_queue -n osint_discovery_worker &
watchmedo auto-restart --recursive --pattern="*.py" --directory="/usr/src/app/reNgine/" -- celery -A reNgine worker --concurrency=50 --pool=gevent --loglevel=info -Q dorking_queue -n dorking_worker &
watchmedo auto-restart --recursive --pattern="*.py" --directory="/usr/src/app/reNgine/" -- celery -A reNgine worker --concurrency=50 --pool=gevent --loglevel=info -Q theHarvester_queue -n theHarvester_worker &
watchmedo auto-restart --recursive --pattern="*.py" --directory="/usr/src/app/reNgine/" -- celery -A reNgine worker --concurrency=50 --pool=gevent --loglevel=info -Q h8mail_queue -n h8mail_worker &
watchmedo auto-restart --recursive --pattern="*.py" --directory="/usr/src/app/reNgine/" -- celery -A reNgine worker --concurrency=100 --pool=gevent --loglevel=info -Q screenshot_queue -n screenshot_worker &
watchmedo auto-restart --recursive --pattern="*.py" --directory="/usr/src/app/reNgine/" -- celery -A reNgine worker --concurrency=100 --pool=gevent --loglevel=info -Q port_scan_queue -n port_scan_worker &
watchmedo auto-restart --recursive --pattern="*.py" --directory="/usr/src/app/reNgine/" -- celery -A reNgine worker --concurrency=100 --pool=gevent --loglevel=info -Q nmap_queue -n nmap_worker &
watchmedo auto-restart --recursive --pattern="*.py" --directory="/usr/src/app/reNgine/" -- celery -A reNgine worker --concurrency=100 --pool=gevent --loglevel=info -Q waf_detection_queue -n waf_detection_worker &
watchmedo auto-restart --recursive --pattern="*.py" --directory="/usr/src/app/reNgine/" -- celery -A reNgine worker --concurrency=100 --pool=gevent --loglevel=info -Q dir_file_fuzz_queue -n dir_file_fuzz_worker &
watchmedo auto-restart --recursive --pattern="*.py" --directory="/usr/src/app/reNgine/" -- celery -A reNgine worker --concurrency=100 --pool=gevent --loglevel=info -Q fetch_url_queue -n fetch_url_worker &
watchmedo auto-restart --recursive --pattern="*.py" --directory="/usr/src/app/reNgine/" -- celery -A reNgine worker --concurrency=100 --pool=gevent --loglevel=info -Q vulnerability_scan_queue -n vulnerability_scan_worker &
watchmedo auto-restart --recursive --pattern="*.py" --directory="/usr/src/app/reNgine/" -- celery -A reNgine worker --concurrency=1000 --pool=gevent --loglevel=info -Q vulnerability_scan_module_queue -n vulnerability_scan_module_worker &
watchmedo auto-restart --recursive --pattern="*.py" --directory="/usr/src/app/reNgine/" -- celery -A reNgine worker --concurrency=100 --pool=gevent --loglevel=info -Q dalfox_xss_scan_queue -n dalfox_xss_scan_worker &
watchmedo auto-restart --recursive --pattern="*.py" --directory="/usr/src/app/reNgine/" -- celery -A reNgine worker --concurrency=100 --pool=gevent --loglevel=info -Q crlfuzz_queue -n crlfuzz_worker &
watchmedo auto-restart --recursive --pattern="*.py" --directory="/usr/src/app/reNgine/" -- celery -A reNgine worker --concurrency=5000 --pool=gevent --loglevel=info -Q http_crawl_queue -n http_crawl_worker &
watchmedo auto-restart --recursive --pattern="*.py" --directory="/usr/src/app/reNgine/" -- celery -A reNgine worker --concurrency=50 --pool=gevent --loglevel=info -Q send_notif_queue -n send_notif_worker &
watchmedo auto-restart --recursive --pattern="*.py" --directory="/usr/src/app/reNgine/" -- celery -A reNgine worker --concurrency=50 --pool=gevent --loglevel=info -Q send_scan_notif_queue -n send_scan_notif_worker &
watchmedo auto-restart --recursive --pattern="*.py" --directory="/usr/src/app/reNgine/" -- celery -A reNgine worker --concurrency=50 --pool=gevent --loglevel=info -Q send_task_notif_queue -n send_task_notif_worker &
watchmedo auto-restart --recursive --pattern="*.py" --directory="/usr/src/app/reNgine/" -- celery -A reNgine worker --concurrency=50 --pool=gevent --loglevel=info -Q send_file_to_discord_queue -n send_file_to_discord_worker &
watchmedo auto-restart --recursive --pattern="*.py" --directory="/usr/src/app/reNgine/" -- celery -A reNgine worker --concurrency=50 --pool=gevent --loglevel=info -Q send_hackerone_report_queue -n send_hackerone_report_worker &
watchmedo auto-restart --recursive --pattern="*.py" --directory="/usr/src/app/reNgine/" -- celery -A reNgine worker --concurrency=50 --pool=gevent --loglevel=info -Q parse_nmap_results_queue -n parse_nmap_results_worker &
watchmedo auto-restart --recursive --pattern="*.py" --directory="/usr/src/app/reNgine/" -- celery -A reNgine worker --concurrency=500 --pool=gevent --loglevel=info -Q geo_localize_queue -n geo_localize_worker &
watchmedo auto-restart --recursive --pattern="*.py" --directory="/usr/src/app/reNgine/" -- celery -A reNgine worker --concurrency=100 --pool=gevent --loglevel=info -Q query_whois_queue -n query_whois_worker &
watchmedo auto-restart --recursive --pattern="*.py" --directory="/usr/src/app/reNgine/" -- celery -A reNgine worker --concurrency=100 --pool=gevent --loglevel=info -Q remove_duplicate_endpoints_queue -n remove_duplicate_endpoints_worker &
watchmedo auto-restart --recursive --pattern="*.py" --directory="/usr/src/app/reNgine/" -- celery -A reNgine worker --concurrency=500 --pool=gevent --loglevel=info -Q run_command_queue -n run_command_worker &
watchmedo auto-restart --recursive --pattern="*.py" --directory="/usr/src/app/reNgine/" -- celery -A reNgine worker --concurrency=100 --pool=gevent --loglevel=info -Q query_reverse_whois_queue -n query_reverse_whois_worker &
watchmedo auto-restart --recursive --pattern="*.py" --directory="/usr/src/app/reNgine/" -- celery -A reNgine worker --concurrency=100 --pool=gevent --loglevel=info -Q query_ip_history_queue -n query_ip_history_worker &
watchmedo auto-restart --recursive --pattern="*.py" --directory="/usr/src/app/reNgine/" -- celery -A reNgine worker --concurrency=100 --pool=gevent --loglevel=info -Q gpt_queue -n gpt_worker &
watchmedo auto-restart --recursive --pattern="*.py" --directory="/usr/src/app/reNgine/" -- celery -A reNgine worker --concurrency=100 --pool=gevent --loglevel=info -Q s3scanner_queue -n s3scanner_worker
exec "$@"

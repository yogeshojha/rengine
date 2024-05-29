#!/bin/bash

poetry run -C $HOME/ python3 manage.py migrate
poetry run -C $HOME/ python3 manage.py collectstatic --no-input --clear

# Load default engines, keywords, and external tools
poetry run -C $HOME/ python3 manage.py loaddata fixtures/default_scan_engines.yaml --app scanEngine.EngineType
poetry run -C $HOME/ python3 manage.py loaddata fixtures/default_keywords.yaml --app scanEngine.InterestingLookupModel
poetry run -C $HOME/ python3 manage.py loaddata fixtures/external_tools.yaml --app scanEngine.InstalledExternalTool

# Compile messages translations
find . -type f -name "*.po" -exec sed -i 's/^#~ //g' {} +
poetry run -C $HOME/ python3 manage.py compilemessages

loglevel='info'
if [ "$DEBUG" == "1" ]; then
    loglevel='debug'
fi

watchmedo auto-restart --recursive --pattern="*.py" --directory="/home/rengine/rengine/" -- poetry run -C $HOME/ celery -A reNgine.tasks worker --loglevel=$loglevel --autoscale=$MAX_CONCURRENCY,$MIN_CONCURRENCY -Q main_scan_queue &
watchmedo auto-restart --recursive --pattern="*.py" --directory="/home/rengine/rengine/" -- poetry run -C $HOME/ celery -A reNgine.tasks worker --pool=gevent --concurrency=30 --loglevel=$loglevel -Q initiate_scan_queue -n initiate_scan_worker &
watchmedo auto-restart --recursive --pattern="*.py" --directory="/home/rengine/rengine/" -- poetry run -C $HOME/ celery -A reNgine.tasks worker --pool=gevent --concurrency=30 --loglevel=$loglevel -Q subscan_queue -n subscan_worker &
watchmedo auto-restart --recursive --pattern="*.py" --directory="/home/rengine/rengine/" -- poetry run -C $HOME/ celery -A reNgine.tasks worker --pool=gevent --concurrency=20 --loglevel=$loglevel -Q report_queue -n report_worker &
watchmedo auto-restart --recursive --pattern="*.py" --directory="/home/rengine/rengine/" -- poetry run -C $HOME/ celery -A reNgine.tasks worker --pool=gevent --concurrency=10 --loglevel=$loglevel -Q send_notif_queue -n send_notif_worker &
watchmedo auto-restart --recursive --pattern="*.py" --directory="/home/rengine/rengine/" -- poetry run -C $HOME/ celery -A reNgine.tasks worker --pool=gevent --concurrency=10 --loglevel=$loglevel -Q send_scan_notif_queue -n send_scan_notif_worker &
watchmedo auto-restart --recursive --pattern="*.py" --directory="/home/rengine/rengine/" -- poetry run -C $HOME/ celery -A reNgine.tasks worker --pool=gevent --concurrency=10 --loglevel=$loglevel -Q send_task_notif_queue -n send_task_notif_worker &
watchmedo auto-restart --recursive --pattern="*.py" --directory="/home/rengine/rengine/" -- poetry run -C $HOME/ celery -A reNgine.tasks worker --pool=gevent --concurrency=5 --loglevel=$loglevel -Q send_file_to_discord_queue -n send_file_to_discord_worker &
watchmedo auto-restart --recursive --pattern="*.py" --directory="/home/rengine/rengine/" -- poetry run -C $HOME/ celery -A reNgine.tasks worker --pool=gevent --concurrency=5 --loglevel=$loglevel -Q send_hackerone_report_queue -n send_hackerone_report_worker &
watchmedo auto-restart --recursive --pattern="*.py" --directory="/home/rengine/rengine/" -- poetry run -C $HOME/ celery -A reNgine.tasks worker --pool=gevent --concurrency=10 --loglevel=$loglevel -Q parse_nmap_results_queue -n parse_nmap_results_worker &
watchmedo auto-restart --recursive --pattern="*.py" --directory="/home/rengine/rengine/" -- poetry run -C $HOME/ celery -A reNgine.tasks worker --pool=gevent --concurrency=20 --loglevel=$loglevel -Q geo_localize_queue -n geo_localize_worker &
watchmedo auto-restart --recursive --pattern="*.py" --directory="/home/rengine/rengine/" -- poetry run -C $HOME/ celery -A reNgine.tasks worker --pool=gevent --concurrency=10 --loglevel=$loglevel -Q query_whois_queue -n query_whois_worker &
watchmedo auto-restart --recursive --pattern="*.py" --directory="/home/rengine/rengine/" -- poetry run -C $HOME/ celery -A reNgine.tasks worker --pool=gevent --concurrency=30 --loglevel=$loglevel -Q remove_duplicate_endpoints_queue -n remove_duplicate_endpoints_worker &
watchmedo auto-restart --recursive --pattern="*.py" --directory="/home/rengine/rengine/" -- poetry run -C $HOME/ celery -A reNgine.tasks worker --pool=gevent --concurrency=50 --loglevel=$loglevel -Q run_command_queue -n run_command_worker &
watchmedo auto-restart --recursive --pattern="*.py" --directory="/home/rengine/rengine/" -- poetry run -C $HOME/ celery -A reNgine.tasks worker --pool=gevent --concurrency=10 --loglevel=$loglevel -Q query_reverse_whois_queue -n query_reverse_whois_worker &
watchmedo auto-restart --recursive --pattern="*.py" --directory="/home/rengine/rengine/" -- poetry run -C $HOME/ celery -A reNgine.tasks worker --pool=gevent --concurrency=10 --loglevel=$loglevel -Q query_ip_history_queue -n query_ip_history_worker &
watchmedo auto-restart --recursive --pattern="*.py" --directory="/home/rengine/rengine/" -- poetry run -C $HOME/ celery -A reNgine.tasks worker --pool=gevent --concurrency=30 --loglevel=$loglevel -Q gpt_queue -n gpt_worker &
watchmedo auto-restart --recursive --pattern="*.py" --directory="/home/rengine/rengine/" -- poetry run -C $HOME/ celery -A reNgine.tasks worker --pool=gevent --concurrency=10 --loglevel=$loglevel -Q dorking_queue -n dorking_worker &
watchmedo auto-restart --recursive --pattern="*.py" --directory="/home/rengine/rengine/" -- poetry run -C $HOME/ celery -A reNgine.tasks worker --pool=gevent --concurrency=10 --loglevel=$loglevel -Q osint_discovery_queue -n osint_discovery_worker &
watchmedo auto-restart --recursive --pattern="*.py" --directory="/home/rengine/rengine/" -- poetry run -C $HOME/ celery -A reNgine.tasks worker --pool=gevent --concurrency=10 --loglevel=$loglevel -Q h8mail_queue -n h8mail_worker &
watchmedo auto-restart --recursive --pattern="*.py" --directory="/home/rengine/rengine/" -- poetry run -C $HOME/ celery -A reNgine.tasks worker --pool=gevent --concurrency=10 --loglevel=$loglevel -Q theHarvester_queue -n theHarvester_worker
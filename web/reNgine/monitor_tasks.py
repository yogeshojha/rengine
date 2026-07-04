import os
import requests
import json
import validators
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from django.utils import timezone
from celery.utils.log import get_task_logger

from reNgine.celery import app
from reNgine.definitions import *
from reNgine.settings import *
from reNgine.common_func import *
from targetApp.models import Domain
from startScan.models import ScanHistory, Subdomain, EndPoint, MonitoringDiscovery
from scanEngine.models import EngineType

logger = get_task_logger(__name__)

@app.task(name='monitor_target_task', queue='main_scan_queue')
def monitor_target_task(domain_id):
	try:
		domain = Domain.objects.get(pk=domain_id)
	except Domain.DoesNotExist:
		logger.error(f"Domain with ID {domain_id} does not exist.")
		return

	logger.info(f"Starting monitoring for {domain.name}")

	# 1. Setup Scan History
	engine = domain.monitor_engine
	if not engine:
		engine = EngineType.objects.filter(default_engine=True).first()

	scan_history = ScanHistory.objects.create(
		domain=domain,
		scan_type=engine,
		start_scan_date=timezone.now(),
		scan_status=RUNNING_TASK,
		tasks=['monitoring_discovery']
	)

	results_dir = f"{RENGINE_RESULTS}/{domain.name}_monitor_{scan_history.id}"
	os.makedirs(results_dir, exist_ok=True)
	scan_history.results_dir = results_dir
	scan_history.save()

	# Context for save_subdomain and save_endpoint
	ctx = {
		'scan_history_id': scan_history.id,
		'domain_id': domain.id,
		'results_dir': results_dir,
	}

	new_discoveries = []

	try:
		# 2. Subdomain Discovery (Subfinder)
		subdomain_file = f"{results_dir}/subdomains_monitor.txt"
		subfinder_cmd = f"subfinder -d {domain.name} -silent -o {subdomain_file}"
		os.system(subfinder_cmd)

		if os.path.exists(subdomain_file):
			with open(subdomain_file, 'r') as f:
				discovered_subs = [line.strip() for line in f if line.strip()]
			
			existing_subs = set(Subdomain.objects.filter(target_domain=domain).values_list('name', flat=True))
			
			for sub_name in discovered_subs:
				if sub_name not in existing_subs:
					# Save new subdomain
					# Note: save_subdomain in tasks.py (imported via *)
					from reNgine.tasks import save_subdomain
					sub_obj, created = save_subdomain(sub_name, ctx=ctx)
					if created:
						new_discoveries.append(f"Subdomain: {sub_name}")
						MonitoringDiscovery.objects.create(
							domain=domain,
							discovery_type='subdomain',
							content={'name': sub_name},
							scan_history=scan_history
						)

		# 3. URL Discovery (GAU)
		url_file = f"{results_dir}/urls_monitor.txt"
		gau_cmd = f"gau {domain.name} --subs --silent -o {url_file}"
		os.system(gau_cmd)

		if os.path.exists(url_file):
			with open(url_file, 'r') as f:
				# Limit to 500 URLs to avoid overload in monitoring
				discovered_urls = [line.strip() for line in f if line.strip()][:500]
			
			existing_urls = set(EndPoint.objects.filter(target_domain=domain).values_list('http_url', flat=True))
			
			for url in discovered_urls:
				if url not in existing_urls:
					# Detect login and status
					status, title, is_login = detect_login_and_status(url)
					
					from reNgine.tasks import save_endpoint
					endpoint_data = {
						'http_status': status,
						'page_title': title,
					}
					endpoint_obj, created = save_endpoint(url, ctx=ctx, **endpoint_data)
					
					if created:
						disc_type = 'login' if is_login else 'directory'
						new_discoveries.append(f"{disc_type.capitalize()}: {url}")
						MonitoringDiscovery.objects.create(
							domain=domain,
							discovery_type=disc_type,
							content={'url': url, 'status': status, 'title': title},
							scan_history=scan_history
						)

		# 4. Notifications
		if new_discoveries:
			message = f"🔍 Monitoring discovery for {domain.name}:\n" + "\n".join(new_discoveries[:10])
			if len(new_discoveries) > 10:
				message += f"\n... and {len(new_discoveries) - 10} more."
			
			send_telegram_message(message)
			send_slack_message(message)
			send_discord_message(message, title=f"Monitoring: {domain.name}", severity='info')
			
			# Create In-App Notification (Toast)
			create_inappnotification(
				title=f"Monitoring Discovery: {domain.name}",
				description=f"Found {len(new_discoveries)} new items.",
				notification_type=PROJECT_LEVEL_NOTIFICATION,
				status='info'
			)

		# 5. Follow-up Scan
		if domain.monitor_scan_scope != 'none' and new_discoveries:
			from reNgine.tasks import initiate_scan
			if domain.monitor_scan_scope == 'targeted':
				# Targeted scan for new subdomains
				new_subs = [d.split(": ")[1] for d in new_discoveries if d.startswith("Subdomain")]
				if new_subs:
					initiate_scan.delay(
						scan_history_id=None,
						domain_id=domain.id,
						engine_id=engine.id,
						scan_type=SCHEDULED_SCAN,
						imported_subdomains=new_subs
					)
			elif domain.monitor_scan_scope == 'full':
				initiate_scan.delay(
					scan_history_id=None,
					domain_id=domain.id,
					engine_id=engine.id,
					scan_type=SCHEDULED_SCAN
				)

		scan_history.scan_status = SUCCESS_TASK
		scan_history.stop_scan_date = timezone.now()
		scan_history.save()
		
		# Update domain's last monitored date
		domain.last_monitored = timezone.now()
		domain.save()

	except Exception as e:
		logger.error(f"Error in monitoring task for {domain.name}: {str(e)}")
		scan_history.scan_status = FAILED_TASK
		scan_history.error_message = str(e)
		scan_history.save()

def detect_login_and_status(url):
	try:
		# Use a random User-Agent from OpSec if possible, or just a default
		headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
		response = requests.get(url, timeout=5, verify=False, headers=headers)
		status = response.status_code
		soup = BeautifulSoup(response.text, 'html.parser')
		title = soup.title.string.strip() if soup.title and soup.title.string else ""
		
		is_login = False
		if soup.find('input', {'type': 'password'}):
			is_login = True
		elif any(keyword in title.lower() for keyword in ['login', 'signin', 'auth', 'portal']):
			is_login = True
			
		return status, title, is_login
	except Exception as e:
		# logger.debug(f"Probing failed for {url}: {str(e)}")
		return 0, "", False

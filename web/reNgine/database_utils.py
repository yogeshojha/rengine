import re
import validators
import logging

from urllib.parse import urlparse
from django.db import transaction
from django.utils import timezone

from dashboard.models import Project
from targetApp.models import Organization, Domain
from startScan.models import EndPoint, IpAddress
from reNgine.settings import LOGGING
from reNgine.common_func import *

logger = logging.getLogger(__name__)

@transaction.atomic
def bulk_import_targets(
	targets: list[dict], 
	project_slug: str, 
	organization_name: str = None, 
	org_description: str = None, 
	h1_team_handle: str = None):
	""" 
		Used to import targets in reNgine

		Args:
			targets (list[dict]): list of targets to import, [{'target': 'target1.com', 'description': 'desc1'}, ...]
			project_slug (str): slug of the project
			organization_name (str): name of the organization to tag these targets
			org_description (str): description of the organization
			h1_team_handle (str): hackerone team handle (if imported from hackerone)

		Returns:
			bool: True if new targets are imported, False otherwise
	"""
	new_targets_imported = False
	project = Project.objects.get(slug=project_slug)

	all_targets = []

	for target in targets:
		name = target.get('name', '').strip()
		description = target.get('description', '')
		
		if not name:
			logger.warning(f"Skipping target with empty name")
			continue
		
		is_domain = validators.domain(name)
		is_ip = validators.ipv4(name) or validators.ipv6(name)
		is_url = validators.url(name)

		logger.info(f'{name} | Domain? {is_domain} | IP? {is_ip} | URL? {is_url}')

		if is_domain:
			target_obj = store_domain(name, project, description, h1_team_handle)
		elif is_url:
			target_obj = store_url(name, project, description, h1_team_handle)
		elif is_ip:
			target_obj = store_ip(name, project, description, h1_team_handle)
		else:
			logger.warning(f'{name} is not supported by reNgine')
			continue

		if target_obj:
			all_targets.append(target_obj)
			new_targets_imported = True

		if organization_name and all_targets:
			org_name = organization_name.strip()
			org, created = Organization.objects.get_or_create(
				name=org_name,
				defaults={
					'project': project,
					'description': org_description or '',
					'insert_date': timezone.now()
				}
			)

			if not created:
				org.project = project
				if org_description:
					org.description = org_description
				if org.insert_date is None:
					org.insert_date = timezone.now()
				org.save()

			# Associate all targets with the organization
			for target in all_targets:
				org.domains.add(target)

			logger.info(f"{'Created' if created else 'Updated'} organization {org_name} with {len(all_targets)} targets")

	return new_targets_imported



def remove_wildcard(input_string):
	"""
		Remove wildcard (*) from the beginning of the input string.
		In future, we may find the meaning of wildcards and try to use in target configs such as out of scope etc
	"""
	return re.sub(r'^\*\.', '', input_string)

def store_domain(domain_name, project, description, h1_team_handle):
	"""
		This function is used to store domain in reNgine
	"""
	existing_domain = Domain.objects.filter(name=domain_name).first()

	if existing_domain:
		logger.info(f'Domain {domain_name} already exists. skipping.')
		return
	
	current_time = timezone.now()

	new_domain = Domain.objects.create(
		name=domain_name,
		description=description,
		h1_team_handle=h1_team_handle,
		project=project,
		insert_date=current_time
	)

	logger.info(f'Added new domain {new_domain.name}')

	return new_domain

def store_url(url, project, description, h1_team_handle):
	parsed_url = urlparse(url)
	http_url = parsed_url.geturl()
	domain_name = parsed_url.netloc

	domain = Domain.objects.filter(name=domain_name).first()

	if domain:
		logger.info(f'Domain {domain_name} already exists. skipping...')

	else:
		domain = Domain.objects.create(
			name=domain_name,
			description=description,
			h1_team_handle=h1_team_handle,
			project=project,
			insert_date=timezone.now()
		)
		logger.info(f'Added new domain {domain.name}')

	EndPoint.objects.get_or_create(
		target_domain=domain,
		http_url=sanitize_url(http_url)
	)

	return domain

def store_ip(ip_address, project, description, h1_team_handle):

	domain = Domain.objects.filter(name=ip_address).first()
	
	if domain:
		logger.info(f'Domain {ip_address} already exists. skipping...')
	else:
		domain = Domain.objects.create(
			name=ip_address,
			description=description,
			h1_team_handle=h1_team_handle,
			project=project,
			insert_date=timezone.now(),
			ip_address_cidr=ip_address
		)
		logger.info(f'Added new domain {domain.name}')
	
	ip_data = get_ip_info(ip_address)
	ip_data = get_ip_info(ip_address)
	ip, created = IpAddress.objects.get_or_create(address=ip_address)
	ip.reverse_pointer = ip_data.reverse_pointer
	ip.is_private = ip_data.is_private
	ip.version = ip_data.version
	ip.save()

	return domain
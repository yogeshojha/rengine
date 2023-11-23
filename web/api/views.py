import logging
import re
import socket
import subprocess

import requests
import validators
from dashboard.models import *
from django.db.models import CharField, Count, F, Q, Value
from django.shortcuts import get_object_or_404
from django.utils import timezone
from packaging import version
from django.template.defaultfilters import slugify
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.status import HTTP_400_BAD_REQUEST

from recon_note.models import *
from reNgine.celery import app
from reNgine.common_func import *
from reNgine.definitions import ABORTED_TASK
from reNgine.tasks import *
from reNgine.gpt import GPTAttackSuggestionGenerator
from reNgine.utilities import is_safe_path
from scanEngine.models import *
from startScan.models import *
from startScan.models import EndPoint
from targetApp.models import *

from .serializers import *

logger = logging.getLogger(__name__)


class GPTAttackSuggestion(APIView):
	def get(self, request):
		req = self.request
		subdomain_id = req.query_params.get('subdomain_id')
		if not subdomain_id:
			return Response({
				'status': False,
				'error': 'Missing GET param Subdomain `subdomain_id`'
			})
		try:
			subdomain = Subdomain.objects.get(id=subdomain_id)
		except Exception as e:
			return Response({
				'status': False,
				'error': 'Subdomain not found with id ' + subdomain_id
			})
		if subdomain.attack_surface:
			return Response({
				'status': True,
				'subdomain_name': subdomain.name,
				'description': subdomain.attack_surface
			})
		ip_addrs = subdomain.ip_addresses.all()
		open_ports_str = ''
		for ip in ip_addrs:
			ports = ip.ports.all()
			for port in ports:
				open_ports_str += f'{port.number}/{port.service_name}, '
		tech_used = ''
		for tech in subdomain.technologies.all():
			tech_used += f'{tech.name}, '
		input = f'''
			Subdomain Name: {subdomain.name}
			Subdomain Page Title: {subdomain.page_title}
			Open Ports: {open_ports_str}
			HTTP Status: {subdomain.http_status}
			Technologies Used: {tech_used}
			Content type: {subdomain.content_type}
			Web Server: {subdomain.webserver}
			Page Content Length: {subdomain.content_length}
		'''
		gpt = GPTAttackSuggestionGenerator()
		response = gpt.get_attack_suggestion(input)
		response['subdomain_name'] = subdomain.name
		if response.get('status'):
			subdomain.attack_surface = response.get('description')
			subdomain.save()
		return Response(response)


class GPTVulnerabilityReportGenerator(APIView):
	def get(self, request):
		req = self.request
		vulnerability_id = req.query_params.get('id')
		if not vulnerability_id:
			return Response({
				'status': False,
				'error': 'Missing GET param Vulnerability `id`'
			})
		task = gpt_vulnerability_description.apply_async(args=(vulnerability_id,))
		response = task.wait()
		return Response(response)


class CreateProjectApi(APIView):
	def get(self, request):
		req = self.request
		project_name = req.query_params.get('name')
		slug = slugify(project_name)
		insert_date = timezone.now()

		try:
			project = Project.objects.create(
				name=project_name,
				slug=slug,
				insert_date =insert_date
			)
			response = {
				'status': True,
				'project_name': project_name
			}
			return Response(response)
		except Exception as e:
			response = {
				'status': False,
				'error': str(e)
			}
			return Response(response, status=HTTP_400_BAD_REQUEST)



class QueryInterestingSubdomains(APIView):
	def get(self, request):
		req = self.request
		scan_id = req.query_params.get('scan_id')
		domain_id = req.query_params.get('target_id')

		if scan_id:
			queryset = get_interesting_subdomains(scan_history=scan_id)
		elif domain_id:
			queryset = get_interesting_subdomains(domain_id=domain_id)
		else:
			queryset = get_interesting_subdomains()

		queryset = queryset.distinct('name')

		return Response(InterestingSubdomainSerializer(queryset, many=True).data)


class ListTargetsDatatableViewSet(viewsets.ModelViewSet):
	queryset = Domain.objects.all()
	serializer_class = DomainSerializer

	def get_queryset(self):
		slug = self.request.GET.get('slug', None)
		if slug:
			self.queryset = self.queryset.filter(project__slug=slug)
		return self.queryset

	def filter_queryset(self, qs):
		qs = self.queryset.filter()
		search_value = self.request.GET.get(u'search[value]', None)
		_order_col = self.request.GET.get(u'order[0][column]', None)
		_order_direction = self.request.GET.get(u'order[0][dir]', None)
		if search_value or _order_col or _order_direction:
			order_col = 'id'
			if _order_col == '2':
				order_col = 'name'
			elif _order_col == '4':
				order_col = 'insert_date'
			elif _order_col == '5':
				order_col = 'start_scan_date'
				if _order_direction == 'desc':
					return qs.order_by(F('start_scan_date').desc(nulls_last=True))
				return qs.order_by(F('start_scan_date').asc(nulls_last=True))


			if _order_direction == 'desc':
				order_col = '-{}'.format(order_col)

			qs = self.queryset.filter(
				Q(name__icontains=search_value) |
				Q(description__icontains=search_value) |
				Q(domains__name__icontains=search_value)
			)
			return qs.order_by(order_col)

		return qs.order_by('-id')



class WafDetector(APIView):
	def get(self, request):
		req = self.request
		url= req.query_params.get('url')
		response = {}
		response['status'] = False

		wafw00f_command = f'wafw00f {url}'
		output = subprocess.check_output(wafw00f_command, shell=True)
		# use regex to get the waf
		regex = "behind \\\\x1b\[1;96m(.*)\\\\x1b"
		group = re.search(regex, str(output))

		if group:
			response['status'] = True
			response['results'] = group.group(1)
		else:
			response['message'] = 'Could not detect any WAF!'

		return Response(response)


class SearchHistoryView(APIView):
	def get(self, request):
		req = self.request

		response = {}
		response['status'] = False

		scan_history = SearchHistory.objects.all().order_by('-id')[:5]

		if scan_history:
			response['status'] = True
			response['results'] = SearchHistorySerializer(scan_history, many=True).data

		return Response(response)


class UniversalSearch(APIView):
	def get(self, request):
		req = self.request
		query = req.query_params.get('query')

		response = {}
		response['status'] = False

		if not query:
			response['message'] = 'No query parameter provided!'
			return Response(response)

		response['results'] = {}

		# search history to be saved
		SearchHistory.objects.get_or_create(
			query=query
		)

		# lookup query in subdomain
		subdomain = Subdomain.objects.filter(
			Q(name__icontains=query) |
			Q(cname__icontains=query) |
			Q(page_title__icontains=query) |
			Q(http_url__icontains=query)
		).distinct('name')
		subdomain_data = SubdomainSerializer(subdomain, many=True).data
		response['results']['subdomains'] = subdomain_data

		endpoint = EndPoint.objects.filter(
			Q(http_url__icontains=query) |
			Q(page_title__icontains=query)
		).distinct('http_url')
		endpoint_data = EndpointSerializer(endpoint, many=True).data
		response['results']['endpoints'] = endpoint_data

		vulnerability = Vulnerability.objects.filter(
			Q(http_url__icontains=query) |
			Q(name__icontains=query) |
			Q(description__icontains=query)
		).distinct()
		vulnerability_data = VulnerabilitySerializer(vulnerability, many=True).data
		response['results']['vulnerabilities'] = vulnerability_data

		response['results']['others'] = {}

		if subdomain_data or endpoint_data or vulnerability_data:
			response['status'] = True

		return Response(response)


class FetchMostCommonVulnerability(APIView):
	def post(self, request):
		req = self.request
		data = req.data

		try:
			limit = data.get('limit', 20)
			project_slug = data.get('slug')
			scan_history_id = data.get('scan_history_id')
			target_id = data.get('target_id')
			is_ignore_info = data.get('ignore_info', False)

			response = {}
			response['status'] = False

			if project_slug:
				project = Project.objects.get(slug=project_slug)
				vulnerabilities = Vulnerability.objects.filter(target_domain__project=project)
			else:
				vulnerabilities = Vulnerability.objects.all()


			if scan_history_id:
				vuln_query = (
					vulnerabilities
					.filter(scan_history__id=scan_history_id)
					.values("name", "severity")
				)
				if is_ignore_info:
					most_common_vulnerabilities = (
						vuln_query
						.exclude(severity=0)
						.annotate(count=Count('name'))
						.order_by("-count")[:limit]
					)
				else:
					most_common_vulnerabilities = (
						vuln_query
						.annotate(count=Count('name'))
						.order_by("-count")[:limit]
					)

			elif target_id:
				vuln_query = vulnerabilities.filter(target_domain__id=target_id).values("name", "severity")
				if is_ignore_info:
					most_common_vulnerabilities = (
						vuln_query
						.exclude(severity=0)
						.annotate(count=Count('name'))
						.order_by("-count")[:limit]
					)
				else:
					most_common_vulnerabilities = (
						vuln_query
						.annotate(count=Count('name'))
						.order_by("-count")[:limit]
					)

			else:
				vuln_query = vulnerabilities.values("name", "severity")
				if is_ignore_info:
					most_common_vulnerabilities = (
						vuln_query.exclude(severity=0)
						.annotate(count=Count('name'))
						.order_by("-count")[:limit]
					)
				else:
					most_common_vulnerabilities = (
						vuln_query.annotate(count=Count('name'))
						.order_by("-count")[:limit]
					)


			most_common_vulnerabilities = [vuln for vuln in most_common_vulnerabilities]

			if most_common_vulnerabilities:
				response['status'] = True
				response['result'] = most_common_vulnerabilities
		except Exception as e:
			print(str(e))
			response = {}

		return Response(response)


class FetchMostVulnerable(APIView):
	def post(self, request):
		req = self.request
		data = req.data

		project_slug = data.get('slug')
		scan_history_id = data.get('scan_history_id')
		target_id = data.get('target_id')
		limit = data.get('limit', 20)
		is_ignore_info = data.get('ignore_info', False)

		response = {}
		response['status'] = False

		if project_slug:
			project = Project.objects.get(slug=project_slug)
			subdomains = Subdomain.objects.filter(target_domain__project=project)
			domains = Domain.objects.filter(project=project)
		else:
			subdomains = Subdomain.objects.all()
			domains = Domain.objects.all()

		if scan_history_id:
			subdomain_query = subdomains.filter(scan_history__id=scan_history_id)
			if is_ignore_info:
				most_vulnerable_subdomains = (
					subdomain_query
					.annotate(
						vuln_count=Count('vulnerability__name', filter=~Q(vulnerability__severity=0))
					)
					.order_by('-vuln_count')
					.exclude(vuln_count=0)[:limit]
				)
			else:
				most_vulnerable_subdomains = (
					subdomain_query
					.annotate(vuln_count=Count('vulnerability__name'))
					.order_by('-vuln_count')
					.exclude(vuln_count=0)[:limit]
				)

				if most_vulnerable_subdomains:
					response['status'] = True
					response['result'] = (
						SubdomainSerializer(
							most_vulnerable_subdomains,
							many=True)
						.data
					)

		elif target_id:
			subdomain_query = subdomains.filter(target_domain__id=target_id)
			if is_ignore_info:
				most_vulnerable_subdomains = (
					subdomain_query
					.annotate(vuln_count=Count('vulnerability__name', filter=~Q(vulnerability__severity=0)))
					.order_by('-vuln_count')
					.exclude(vuln_count=0)[:limit]
				)
			else:
				most_vulnerable_subdomains = (
					subdomain_query
					.annotate(vuln_count=Count('vulnerability__name'))
					.order_by('-vuln_count')
					.exclude(vuln_count=0)[:limit]
				)

			if most_vulnerable_subdomains:
				response['status'] = True
				response['result'] = (
					SubdomainSerializer(
						most_vulnerable_subdomains,
						many=True)
					.data
				)
		else:
			if is_ignore_info:
				most_vulnerable_targets = (
					domains
					.annotate(vuln_count=Count('subdomain__vulnerability__name', filter=~Q(subdomain__vulnerability__severity=0)))
					.order_by('-vuln_count')
					.exclude(vuln_count=0)[:limit]
				)
			else:
				most_vulnerable_targets = (
					domains
					.annotate(vuln_count=Count('subdomain__vulnerability__name'))
					.order_by('-vuln_count')
					.exclude(vuln_count=0)[:limit]
				)

			if most_vulnerable_targets:
				response['status'] = True
				response['result'] = (
					DomainSerializer(
						most_vulnerable_targets,
						many=True)
					.data
				)

		return Response(response)


class CVEDetails(APIView):
	def get(self, request):
		req = self.request

		cve_id = req.query_params.get('cve_id')

		if not cve_id:
			return Response({'status': False, 'message': 'CVE ID not provided'})

		response = requests.get('https://cve.circl.lu/api/cve/' + cve_id)

		if response.status_code != 200:
			return  Response({'status': False, 'message': 'Unknown Error Occured!'})

		if not response.json():
			return  Response({'status': False, 'message': 'CVE ID does not exists.'})

		return Response({'status': True, 'result': response.json()})


class AddReconNote(APIView):
	def post(self, request):
		req = self.request
		data = req.data

		subdomain_id = data.get('subdomain_id')
		scan_history_id = data.get('scan_history_id')
		title = data.get('title')
		description = data.get('description')
		project = data.get('project')

		try:
			project = Project.objects.get(slug=project)
			note = TodoNote()
			note.title = title
			note.description = description

			if scan_history_id:
				scan_history = ScanHistory.objects.get(id=scan_history_id)
				note.scan_history = scan_history

			# get scan history for subdomain_id
			if subdomain_id:
				subdomain = Subdomain.objects.get(id=subdomain_id)
				note.subdomain = subdomain

				# also get scan history
				scan_history_id = subdomain.scan_history.id
				scan_history = ScanHistory.objects.get(id=scan_history_id)
				note.scan_history = scan_history

			note.project = project
			note.save()
			response = {'status': True}
		except Exception as e:
			response = {'status': False, 'message': str(e)}

		return Response(response)


class ToggleSubdomainImportantStatus(APIView):
	def post(self, request):
		req = self.request
		data = req.data

		subdomain_id = data.get('subdomain_id')

		response = {'status': False, 'message': 'No subdomain_id provided'}

		name = Subdomain.objects.get(id=subdomain_id)
		name.is_important = not name.is_important
		name.save()

		response = {'status': True}

		return Response(response)


class AddTarget(APIView):
	def post(self, request):
		req = self.request
		data = req.data
		h1_team_handle = data.get('h1_team_handle')
		description = data.get('description')
		domain_name = data.get('domain_name')
		slug = data.get('slug')

		# Validate domain name
		if not validators.domain(domain_name):
			return Response({'status': False, 'message': 'Invalid domain or IP'})

		project = Project.objects.get(slug=slug)

		# Create domain object in DB
		domain, _ = Domain.objects.get_or_create(name=domain_name)
		domain.project = project
		domain.h1_team_handle = h1_team_handle
		domain.description = description
		if not domain.insert_date:
			domain.insert_date = timezone.now()
		domain.save()
		return Response({
			'status': True,
			'message': 'Domain successfully added as target !',
			'domain_name': domain_name,
			'domain_id': domain.id
		})


class FetchSubscanResults(APIView):
	def get(self, request):
		req = self.request
		# data = req.data
		subscan_id = req.query_params.get('subscan_id')
		subscan = SubScan.objects.filter(id=subscan_id)
		if not subscan.exists():
			return Response({
				'status': False,
				'error': f'Subscan {subscan_id} does not exist'
			})

		subscan_data = SubScanResultSerializer(subscan.first(), many=False).data
		task_name = subscan_data['type']
		subscan_results = []

		if task_name == 'port_scan':
			ips_in_subscan = IpAddress.objects.filter(ip_subscan_ids__in=subscan)
			subscan_results = IpSerializer(ips_in_subscan, many=True).data

		elif task_name == 'vulnerability_scan':
			vulns_in_subscan = Vulnerability.objects.filter(vuln_subscan_ids__in=subscan)
			subscan_results = VulnerabilitySerializer(vulns_in_subscan, many=True).data

		elif task_name == 'fetch_url':
			endpoints_in_subscan = EndPoint.objects.filter(endpoint_subscan_ids__in=subscan)
			subscan_results = EndpointSerializer(endpoints_in_subscan, many=True).data

		elif task_name == 'dir_file_fuzz':
			dirs_in_subscan = DirectoryScan.objects.filter(dir_subscan_ids__in=subscan)
			subscan_results = DirectoryScanSerializer(dirs_in_subscan, many=True).data

		elif task_name == 'subdomain_discovery':
			subdomains_in_subscan = Subdomain.objects.filter(subdomain_subscan_ids__in=subscan)
			subscan_results = SubdomainSerializer(subdomains_in_subscan, many=True).data

		elif task_name == 'screenshot':
			subdomains_in_subscan = Subdomain.objects.filter(subdomain_subscan_ids__in=subscan, screenshot_path__isnull=False)
			subscan_results = SubdomainSerializer(subdomains_in_subscan, many=True).data

		logger.info(subscan_data)
		logger.info(subscan_results)

		return Response({'subscan': subscan_data, 'result': subscan_results})


class ListSubScans(APIView):
	def post(self, request):
		req = self.request
		data = req.data
		subdomain_id = data.get('subdomain_id', None)
		scan_history = data.get('scan_history_id', None)
		domain_id = data.get('domain_id', None)
		response = {}
		response['status'] = False

		if subdomain_id:
			subscans = (
				SubScan.objects
				.filter(subdomain__id=subdomain_id)
				.order_by('-stop_scan_date')
			)
			results = SubScanSerializer(subscans, many=True).data
			if subscans:
				response['status'] = True
				response['results'] = results

		elif scan_history:
			subscans = (
				SubScan.objects
				.filter(scan_history__id=scan_history)
				.order_by('-stop_scan_date')
			)
			results = SubScanSerializer(subscans, many=True).data
			if subscans:
				response['status'] = True
				response['results'] = results

		elif domain_id:
			scan_history = ScanHistory.objects.filter(domain__id=domain_id)
			subscans = (
				SubScan.objects
				.filter(scan_history__in=scan_history)
				.order_by('-stop_scan_date')
			)
			results = SubScanSerializer(subscans, many=True).data
			if subscans:
				response['status'] = True
				response['results'] = results

		return Response(response)


class DeleteMultipleRows(APIView):
	def post(self, request):
		req = self.request
		data = req.data

		try:
			if data['type'] == 'subscan':
				for row in data['rows']:
					SubScan.objects.get(id=row).delete()
			response = True
		except Exception as e:
			response = False

		return Response({'status': response})


class StopScan(APIView):
	def post(self, request):
		req = self.request
		data = req.data
		scan_id = data.get('scan_id')
		subscan_id = data.get('subscan_id')
		response = {}
		task_ids = []
		scan = None
		subscan = None
		if subscan_id:
			try:
				subscan = get_object_or_404(SubScan, id=subscan_id)
				scan = subscan.scan_history
				task_ids = subscan.celery_ids
				subscan.status = ABORTED_TASK
				subscan.stop_scan_date = timezone.now()
				subscan.save()
				create_scan_activity(
					subscan.scan_history.id,
					f'Subscan {subscan_id} aborted',
					SUCCESS_TASK)
				response['status'] = True
			except Exception as e:
				logging.error(e)
				response = {'status': False, 'message': str(e)}
		elif scan_id:
			try:
				scan = get_object_or_404(ScanHistory, id=scan_id)
				task_ids = scan.celery_ids
				scan.scan_status = ABORTED_TASK
				scan.stop_scan_date = timezone.now()
				scan.save()
				create_scan_activity(
					scan.id,
					"Scan aborted",
					SUCCESS_TASK)
				response['status'] = True
			except Exception as e:
				logging.error(e)
				response = {'status': False, 'message': str(e)}

		logger.warning(f'Revoking tasks {task_ids}')
		for task_id in task_ids:
			app.control.revoke(task_id, terminate=True, signal='SIGKILL')

		# Abort running tasks
		tasks = (
			ScanActivity.objects
			.filter(scan_of=scan)
			.filter(status=RUNNING_TASK)
			.order_by('-pk')
		)
		if tasks.exists():
			for task in tasks:
				if subscan_id and task.id not in subscan.celery_ids:
					continue
				task.status = ABORTED_TASK
				task.time = timezone.now()
				task.save()

		return Response(response)


class InitiateSubTask(APIView):
	def post(self, request):
		req = self.request
		data = req.data
		engine_id = data.get('engine_id')
		scan_types = data['tasks']
		for subdomain_id in data['subdomain_ids']:
			logger.info(f'Running subscans {scan_types} on subdomain "{subdomain_id}" ...')
			for stype in scan_types:
				ctx = {
					'scan_history_id': None,
					'subdomain_id': subdomain_id,
					'scan_type': stype,
					'engine_id': engine_id
				}
				initiate_subscan.apply_async(kwargs=ctx)
		return Response({'status': True})


class DeleteSubdomain(APIView):
	def post(self, request):
		req = self.request
		for id in req.data['subdomain_ids']:
			Subdomain.objects.get(id=id).delete()
		return Response({'status': True})


class DeleteVulnerability(APIView):
	def post(self, request):
		req = self.request
		for id in req.data['vulnerability_ids']:
			Vulnerability.objects.get(id=id).delete()
		return Response({'status': True})


class ListInterestingKeywords(APIView):
	def get(self, request, format=None):
		req = self.request
		keywords = get_lookup_keywords()
		return Response(keywords)


class RengineUpdateCheck(APIView):
	def get(self, request):
		req = self.request
		github_api = \
			'https://api.github.com/repos/yogeshojha/rengine/releases'
		response = requests.get(github_api).json()
		if 'message' in response:
			return Response({'status': False, 'message': 'RateLimited'})

		return_response = {}

		# get current version_number
		# remove quotes from current_version
		current_version = ((os.environ['RENGINE_CURRENT_VERSION'
							])[1:] if os.environ['RENGINE_CURRENT_VERSION'
							][0] == 'v'
							else os.environ['RENGINE_CURRENT_VERSION']).replace("'", "")

		# for consistency remove v from both if exists
		latest_version = re.search(r'v(\d+\.)?(\d+\.)?(\*|\d+)',
								   ((response[0]['name'
								   ])[1:] if response[0]['name'][0] == 'v'
									else response[0]['name']))

		latest_version = latest_version.group(0) if latest_version else None

		if not latest_version:
			latest_version = re.search(r'(\d+\.)?(\d+\.)?(\*|\d+)',
										((response[0]['name'
										])[1:] if response[0]['name'][0]
										== 'v' else response[0]['name']))
			if latest_version:
				latest_version = latest_version.group(0)

		return_response['status'] = True
		return_response['latest_version'] = latest_version
		return_response['current_version'] = current_version
		return_response['update_available'] = version.parse(current_version) < version.parse(latest_version)
		if version.parse(current_version) < version.parse(latest_version):
			return_response['changelog'] = response[0]['body']

		return Response(return_response)


class UninstallTool(APIView):
	def get(self, request):
		req = self.request
		tool_id = req.query_params.get('tool_id')
		tool_name = req.query_params.get('name')

		if tool_id:
			tool = InstalledExternalTool.objects.get(id=tool_id)
		elif tool_name:
			tool = InstalledExternalTool.objects.get(name=tool_name)


		if tool.is_default:
			return Response({'status': False, 'message': 'Default tools can not be uninstalled'})

		# check install instructions, if it is installed using go, then remove from go bin path,
		# else try to remove from github clone path

		# getting tool name is tricky!

		if 'go install' in tool.install_command:
			tool_name = tool.install_command.split('/')[-1].split('@')[0]
			uninstall_command = 'rm /go/bin/' + tool_name
		elif 'git clone' in tool.install_command:
			tool_name = tool.install_command[:-1] if tool.install_command[-1] == '/' else tool.install_command
			tool_name = tool_name.split('/')[-1]
			uninstall_command = 'rm -rf ' + tool.github_clone_path
		else:
			return Response({'status': False, 'message': 'Cannot uninstall tool!'})

		run_command(uninstall_command)
		run_command.apply_async(args=(uninstall_command,))

		tool.delete()

		return Response({'status': True, 'message': 'Uninstall Tool Success'})


class UpdateTool(APIView):
	def get(self, request):
		req = self.request
		tool_id = req.query_params.get('tool_id')
		tool_name = req.query_params.get('name')

		if tool_id:
			tool = InstalledExternalTool.objects.get(id=tool_id)
		elif tool_name:
			tool = InstalledExternalTool.objects.get(name=tool_name)

		# if git clone was used for installation, then we must use git pull inside project directory,
		# otherwise use the same command as given

		update_command = tool.update_command.lower()

		if not update_command:
			return Response({'status': False, 'message': tool.name + 'has missing update command! Cannot update the tool.'})
		elif update_command == 'git pull':
			tool_name = tool.install_command[:-1] if tool.install_command[-1] == '/' else tool.install_command
			tool_name = tool_name.split('/')[-1]
			update_command = 'cd /usr/src/github/' + tool_name + ' && git pull && cd -'

		run_command(update_command)
		run_command.apply_async(args=(update_command,))
		return Response({'status': True, 'message': tool.name + ' updated successfully.'})


class GetExternalToolCurrentVersion(APIView):
	def get(self, request):
		req = self.request
		# toolname is also the command
		tool_id = req.query_params.get('tool_id')
		tool_name = req.query_params.get('name')
		# can supply either tool id or tool_name

		tool = None

		if tool_id:
			if not InstalledExternalTool.objects.filter(id=tool_id).exists():
				return Response({'status': False, 'message': 'Tool Not found'})
			tool = InstalledExternalTool.objects.get(id=tool_id)
		elif tool_name:
			if not InstalledExternalTool.objects.filter(name=tool_name).exists():
				return Response({'status': False, 'message': 'Tool Not found'})
			tool = InstalledExternalTool.objects.get(name=tool_name)

		if not tool.version_lookup_command:
			return Response({'status': False, 'message': 'Version Lookup command not provided.'})

		version_number = None
		_, stdout = run_command(tool.version_lookup_command)
		version_number = re.search(re.compile(tool.version_match_regex), str(stdout))
		if not version_number:
			return Response({'status': False, 'message': 'Invalid version lookup command.'})

		return Response({'status': True, 'version_number': version_number.group(0), 'tool_name': tool.name})



class GithubToolCheckGetLatestRelease(APIView):
	def get(self, request):
		req = self.request

		tool_id = req.query_params.get('tool_id')
		tool_name = req.query_params.get('name')

		if not InstalledExternalTool.objects.filter(id=tool_id).exists():
			return Response({'status': False, 'message': 'Tool Not found'})

		if tool_id:
			tool = InstalledExternalTool.objects.get(id=tool_id)
		elif tool_name:
			tool = InstalledExternalTool.objects.get(name=tool_name)

		if not tool.github_url:
			return Response({'status': False, 'message': 'Github URL is not provided, Cannot check updates'})

		# if tool_github_url has https://github.com/ remove and also remove trailing /
		tool_github_url = tool.github_url.replace('http://github.com/', '').replace('https://github.com/', '')
		tool_github_url = remove_lead_and_trail_slash(tool_github_url)
		github_api = 'https://api.github.com/repos/{}/releases'.format(tool_github_url)
		response = requests.get(github_api).json()
		# check if api rate limit exceeded
		if 'message' in response and response['message'] == 'RateLimited':
			return Response({'status': False, 'message': 'RateLimited'})
		elif 'message' in response and response['message'] == 'Not Found':
			return Response({'status': False, 'message': 'Not Found'})
		elif not response:
			return Response({'status': False, 'message': 'Not Found'})
		
		# only send latest release
		response = response[0]

		api_response = {
			'status': True,
			'url': response['url'],
			'id': response['id'],
			'name': response['name'],
			'changelog': response['body'],
		}
		return Response(api_response)


class ScanStatus(APIView):
	def get(self, request):
		req = self.request
		slug = self.request.GET.get('project', None)
		# main tasks
		recently_completed_scans = (
			ScanHistory.objects
			.filter(domain__project__slug=slug)
			.order_by('-start_scan_date')
			.filter(Q(scan_status=0) | Q(scan_status=2) | Q(scan_status=3))[:10]
		)
		current_scans = (
			ScanHistory.objects
			.filter(domain__project__slug=slug)
			.order_by('-start_scan_date')
			.filter(scan_status=1)
		)
		pending_scans = (
			ScanHistory.objects
			.filter(domain__project__slug=slug)
			.filter(scan_status=-1)
		)

		# subtasks
		recently_completed_tasks = (
			SubScan.objects
			.filter(scan_history__domain__project__slug=slug)
			.order_by('-start_scan_date')
			.filter(Q(status=0) | Q(status=2) | Q(status=3))[:15]
		)
		current_tasks = (
			SubScan.objects
			.filter(scan_history__domain__project__slug=slug)
			.order_by('-start_scan_date')
			.filter(status=1)
		)
		pending_tasks = (
			SubScan.objects
			.filter(scan_history__domain__project__slug=slug)
			.filter(status=-1)
		)
		response = {
			'scans': {
				'pending': ScanHistorySerializer(pending_scans, many=True).data,
				'scanning': ScanHistorySerializer(current_scans, many=True).data,
				'completed': ScanHistorySerializer(recently_completed_scans, many=True).data
			},
			'tasks': {
				'pending': SubScanSerializer(pending_tasks, many=True).data,
				'running': SubScanSerializer(current_tasks, many=True).data,
				'completed': SubScanSerializer(recently_completed_tasks, many=True).data
			}
		}
		return Response(response)


class Whois(APIView):
	def get(self, request):
		req = self.request
		ip_domain = req.query_params.get('ip_domain')
		if not (validators.domain(ip_domain) or validators.ipv4(ip_domain) or validators.ipv6(ip_domain)):
			print(f'Ip address or domain "{ip_domain}" did not pass validator.')
			return Response({'status': False, 'message': 'Invalid domain or IP'})
		is_force_update = req.query_params.get('is_reload')
		is_force_update = True if is_force_update and 'true' == is_force_update.lower() else False
		task = query_whois.apply_async(args=(ip_domain,is_force_update))
		response = task.wait()
		return Response(response)


class ReverseWhois(APIView):
	def get(self, request):
		req = self.request
		lookup_keyword = req.query_params.get('lookup_keyword')
		task = query_reverse_whois.apply_async(args=(lookup_keyword,))
		response = task.wait()
		return Response(response)


class DomainIPHistory(APIView):
	def get(self, request):
		req = self.request
		domain = req.query_params.get('domain')
		task = query_ip_history.apply_async(args=(domain,))
		response = task.wait()
		return Response(response)


class CMSDetector(APIView):
	def get(self, request):
		req = self.request
		url = req.query_params.get('url')
		#save_db = True if 'save_db' in req.query_params else False
		response = {'status': False}
		try:
			response = get_cms_details(url)
		except Exception as e:
			response = {'status': False, 'message': str(e)}
		return Response(response)


class IPToDomain(APIView):
	def get(self, request):
		req = self.request
		ip_address = req.query_params.get('ip_address')
		if not ip_address:
			return Response({
				'status': False,
				'message': 'IP Address Required'
			})
		try:
			logger.info(f'Resolving IP address {ip_address} ...')
			domain, domains, ips = socket.gethostbyaddr(ip_address)
			response = {
				'status': True,
				'ip_address': ip_address,
				'domains': domains or [domain],
				'resolves_to': domain
			}
		except socket.herror: # ip does not have a PTR record
			logger.info(f'No PTR record for {ip_address}')
			response = {
				'status': True,
				'ip_address': ip_address,
				'domains': [ip_address],
				'resolves_to': ip_address
			}
		except Exception as e:
			logger.exception(e)
			response = {
				'status': False,
				'ip_address': ip_address,
				'message': 'Exception {}'.format(e)
			}
		finally:
			return Response(response)


class VulnerabilityReport(APIView):
	def get(self, request):
		req = self.request
		vulnerability_id = req.query_params.get('vulnerability_id')
		return Response({"status": send_hackerone_report(vulnerability_id)})


class GetFileContents(APIView):
	def get(self, request, format=None):
		req = self.request
		name = req.query_params.get('name')

		response = {}
		response['status'] = False

		if 'nuclei_config' in req.query_params:
			path = "/root/.config/nuclei/config.yaml"
			if not os.path.exists(path):
				run_command(f'touch {path}')
				response['message'] = 'File Created!'
			f = open(path, "r")
			response['status'] = True
			response['content'] = f.read()
			return Response(response)

		if 'subfinder_config' in req.query_params:
			path = "/root/.config/subfinder/config.yaml"
			if not os.path.exists(path):
				run_command(f'touch {path}')
				response['message'] = 'File Created!'
			f = open(path, "r")
			response['status'] = True
			response['content'] = f.read()
			return Response(response)

		if 'naabu_config' in req.query_params:
			path = "/root/.config/naabu/config.yaml"
			if not os.path.exists(path):
				run_command(f'touch {path}')
				response['message'] = 'File Created!'
			f = open(path, "r")
			response['status'] = True
			response['content'] = f.read()
			return Response(response)

		if 'theharvester_config' in req.query_params:
			path = "/usr/src/github/theHarvester/api-keys.yaml"
			if not os.path.exists(path):
				run_command(f'touch {path}')
				response['message'] = 'File Created!'
			f = open(path, "r")
			response['status'] = True
			response['content'] = f.read()
			return Response(response)

		if 'amass_config' in req.query_params:
			path = "/root/.config/amass.ini"
			if not os.path.exists(path):
				run_command(f'touch {path}')
				response['message'] = 'File Created!'
			f = open(path, "r")
			response['status'] = True
			response['content'] = f.read()
			return Response(response)

		if 'gf_pattern' in req.query_params:
			basedir = '/root/.gf'
			path = f'/root/.gf/{name}.json'
			if is_safe_path(basedir, path) and os.path.exists(path):
				content = open(path, "r").read()
				response['status'] = True
				response['content'] = content
			else:
				response['message'] = "Invalid path!"
				response['status'] = False
			return Response(response)


		if 'nuclei_template' in req.query_params:
			safe_dir = '/root/nuclei-templates'
			path = f'/root/nuclei-templates/{name}'
			if is_safe_path(safe_dir, path) and os.path.exists(path):
				content = open(path.format(name), "r").read()
				response['status'] = True
				response['content'] = content
			else:
				response['message'] = 'Invalid Path!'
				response['status'] = False
			return Response(response)

		response['message'] = 'Invalid Query Params'
		return Response(response)


class ListTodoNotes(APIView):
	def get(self, request, format=None):
		req = self.request
		notes = TodoNote.objects.all().order_by('-id')
		scan_id = req.query_params.get('scan_id')
		project = req.query_params.get('project')
		if project:
			notes = notes.filter(project__slug=project)
		target_id = req.query_params.get('target_id')
		todo_id = req.query_params.get('todo_id')
		subdomain_id = req.query_params.get('subdomain_id')
		if target_id:
			notes = notes.filter(scan_history__in=ScanHistory.objects.filter(domain__id=target_id))
		elif scan_id:
			notes = notes.filter(scan_history__id=scan_id)
		if todo_id:
			notes = notes.filter(id=todo_id)
		if subdomain_id:
			notes = notes.filter(subdomain__id=subdomain_id)
		notes = ReconNoteSerializer(notes, many=True)
		return Response({'notes': notes.data})


class ListScanHistory(APIView):
	def get(self, request, format=None):
		req = self.request
		scan_history = ScanHistory.objects.all().order_by('-start_scan_date')
		project = req.query_params.get('project')
		if project:
			scan_history = scan_history.filter(domain__project__slug=project)
		scan_history = ScanHistorySerializer(scan_history, many=True)
		return Response(scan_history.data)


class ListEngines(APIView):
	def get(self, request, format=None):
		req = self.request
		engines = EngineType.objects.order_by('engine_name').all()
		engine_serializer = EngineSerializer(engines, many=True)
		return Response({'engines': engine_serializer.data})


class ListOrganizations(APIView):
	def get(self, request, format=None):
		req = self.request
		organizations = Organization.objects.all()
		organization_serializer = OrganizationSerializer(organizations, many=True)
		return Response({'organizations': organization_serializer.data})


class ListTargetsInOrganization(APIView):
	def get(self, request, format=None):
		req = self.request
		organization_id = req.query_params.get('organization_id')
		organization = Organization.objects.filter(id=organization_id)
		targets = Domain.objects.filter(domains__in=organization)
		organization_serializer = OrganizationSerializer(organization, many=True)
		targets_serializer = OrganizationTargetsSerializer(targets, many=True)
		return Response({'organization': organization_serializer.data, 'domains': targets_serializer.data})


class ListTargetsWithoutOrganization(APIView):
	def get(self, request, format=None):
		req = self.request
		targets = Domain.objects.exclude(domains__in=Organization.objects.all())
		targets_serializer = OrganizationTargetsSerializer(targets, many=True)
		return Response({'domains': targets_serializer.data})


class VisualiseData(APIView):
	def get(self, request, format=None):
		req = self.request
		scan_id = req.query_params.get('scan_id')
		if scan_id:
			mitch_data = ScanHistory.objects.filter(id=scan_id)
			serializer = VisualiseDataSerializer(mitch_data, many=True)
			return Response(serializer.data)
		else:
			return Response()


class ListTechnology(APIView):
	def get(self, request, format=None):
		req = self.request
		scan_id = req.query_params.get('scan_id')
		target_id = req.query_params.get('target_id')

		if target_id:
			tech = Technology.objects.filter(
				technologies__in=Subdomain.objects.filter(
					target_domain__id=target_id)).annotate(
				count=Count('name')).order_by('-count')
			serializer = TechnologyCountSerializer(tech, many=True)
			return Response({"technologies": serializer.data})
		elif scan_id:
			tech = Technology.objects.filter(
				technologies__in=Subdomain.objects.filter(
					scan_history__id=scan_id)).annotate(
				count=Count('name')).order_by('-count')
			serializer = TechnologyCountSerializer(tech, many=True)
			return Response({"technologies": serializer.data})
		else:
			tech = Technology.objects.filter(
				technologies__in=Subdomain.objects.all()).annotate(
				count=Count('name')).order_by('-count')
			serializer = TechnologyCountSerializer(tech, many=True)
			return Response({"technologies": serializer.data})


class ListDorkTypes(APIView):
	def get(self, request, format=None):
		req = self.request
		scan_id = req.query_params.get('scan_id')
		if scan_id:
			dork = Dork.objects.filter(
				dorks__in=ScanHistory.objects.filter(id=scan_id)
			).values('type').annotate(count=Count('type')).order_by('-count')
			serializer = DorkCountSerializer(dork, many=True)
			return Response({"dorks": serializer.data})
		else:
			dork = Dork.objects.filter(
				dorks__in=ScanHistory.objects.all()
			).values('type').annotate(count=Count('type')).order_by('-count')
			serializer = DorkCountSerializer(dork, many=True)
			return Response({"dorks": serializer.data})


class ListEmails(APIView):
	def get(self, request, format=None):
		req = self.request
		scan_id = req.query_params.get('scan_id')
		if scan_id:
			email = Email.objects.filter(
				emails__in=ScanHistory.objects.filter(id=scan_id)).order_by('password')
			serializer = EmailSerializer(email, many=True)
			return Response({"emails": serializer.data})


class ListDorks(APIView):
	def get(self, request, format=None):
		req = self.request
		scan_id = req.query_params.get('scan_id')
		type = req.query_params.get('type')
		if scan_id:
			dork = Dork.objects.filter(
				dorks__in=ScanHistory.objects.filter(id=scan_id))
		else:
			dork = Dork.objects.filter(
				dorks__in=ScanHistory.objects.all())
		if scan_id and type:
			dork = dork.filter(type=type)
		serializer = DorkSerializer(dork, many=True)
		grouped_res = {}
		for item in serializer.data:
			item_type = item['type']
			if item_type not in grouped_res:
				grouped_res[item_type] = []
			grouped_res[item_type].append(item)
		return Response({"dorks": grouped_res})


class ListEmployees(APIView):
	def get(self, request, format=None):
		req = self.request
		scan_id = req.query_params.get('scan_id')
		if scan_id:
			employee = Employee.objects.filter(
				employees__in=ScanHistory.objects.filter(id=scan_id))
			serializer = EmployeeSerializer(employee, many=True)
			return Response({"employees": serializer.data})


class ListPorts(APIView):
	def get(self, request, format=None):
		req = self.request
		scan_id = req.query_params.get('scan_id')
		target_id = req.query_params.get('target_id')
		ip_address = req.query_params.get('ip_address')

		if target_id:
			port = Port.objects.filter(
				ports__in=IpAddress.objects.filter(
					ip_addresses__in=Subdomain.objects.filter(
						target_domain__id=target_id))).distinct()
		elif scan_id:
			port = Port.objects.filter(
				ports__in=IpAddress.objects.filter(
					ip_addresses__in=Subdomain.objects.filter(
						scan_history__id=scan_id))).distinct()
		else:
			port = Port.objects.filter(
				ports__in=IpAddress.objects.filter(
					ip_addresses__in=Subdomain.objects.all())).distinct()

		if ip_address:
			port = port.filter(ports__address=ip_address).distinct()

		serializer = PortSerializer(port, many=True)
		return Response({"ports": serializer.data})


class ListSubdomains(APIView):
	def get(self, request, format=None):
		req = self.request
		scan_id = req.query_params.get('scan_id')
		project = req.query_params.get('project')
		target_id = req.query_params.get('target_id')
		ip_address = req.query_params.get('ip_address')
		port = req.query_params.get('port')
		tech = req.query_params.get('tech')

		subdomains = Subdomain.objects.filter(target_domain__project__slug=project) if project else Subdomain.objects.all()

		if scan_id:
			subdomain_query = subdomains.filter(scan_history__id=scan_id).distinct('name')
		elif target_id:
			subdomain_query = subdomains.filter(target_domain__id=target_id).distinct('name')
		else:
			subdomain_query = subdomains.all().distinct('name')

		if ip_address:
			subdomain_query = subdomain_query.filter(ip_addresses__address=ip_address)

		if tech:
			subdomain_query = subdomain_query.filter(technologies__name=tech)

		if port:
			subdomain_query = subdomain_query.filter(
				ip_addresses__in=IpAddress.objects.filter(
					ports__in=Port.objects.filter(
						number=port)))

		if 'only_important' in req.query_params:
			subdomain_query = subdomain_query.filter(is_important=True)


		if 'no_lookup_interesting' in req.query_params:
			serializer = OnlySubdomainNameSerializer(subdomain_query, many=True)
		else:
			serializer = SubdomainSerializer(subdomain_query, many=True)
		return Response({"subdomains": serializer.data})

	def post(self, req):
		req = self.request
		data = req.data

		subdomain_ids = data.get('subdomain_ids')

		subdomain_names = []

		for id in subdomain_ids:
			subdomain_names.append(Subdomain.objects.get(id=id).name)

		if subdomain_names:
			return Response({'status': True, "results": subdomain_names})

		return Response({'status': False})



class ListOsintUsers(APIView):
	def get(self, request, format=None):
		req = self.request
		scan_id = req.query_params.get('scan_id')
		if scan_id:
			documents = MetaFinderDocument.objects.filter(scan_history__id=scan_id).exclude(author__isnull=True).values('author').distinct()
			serializer = MetafinderUserSerializer(documents, many=True)
			return Response({"users": serializer.data})


class ListMetadata(APIView):
	def get(self, request, format=None):
		req = self.request
		scan_id = req.query_params.get('scan_id')
		if scan_id:
			documents = MetaFinderDocument.objects.filter(scan_history__id=scan_id).distinct()
			serializer = MetafinderDocumentSerializer(documents, many=True)
			return Response({"metadata": serializer.data})


class ListIPs(APIView):
	def get(self, request, format=None):
		req = self.request
		scan_id = req.query_params.get('scan_id')
		target_id = req.query_params.get('target_id')

		port = req.query_params.get('port')

		if target_id:
			ips = IpAddress.objects.filter(
				ip_addresses__in=Subdomain.objects.filter(
					target_domain__id=target_id)).distinct()
		elif scan_id:
			ips = IpAddress.objects.filter(
				ip_addresses__in=Subdomain.objects.filter(
					scan_history__id=scan_id)).distinct()
		else:
			ips = IpAddress.objects.filter(
				ip_addresses__in=Subdomain.objects.all()).distinct()

		if port:
			ips = ips.filter(
				ports__in=Port.objects.filter(
					number=port)).distinct()


		serializer = IpSerializer(ips, many=True)
		return Response({"ips": serializer.data})


class IpAddressViewSet(viewsets.ModelViewSet):
	queryset = Subdomain.objects.none()
	serializer_class = IpSubdomainSerializer

	def get_queryset(self):
		req = self.request
		scan_id = req.query_params.get('scan_id')

		if scan_id:
			self.queryset = Subdomain.objects.filter(
				scan_history__id=scan_id).exclude(
				ip_addresses__isnull=True).distinct()
		else:
			self.serializer_class = IpSerializer
			self.queryset = IpAddress.objects.all()
		return self.queryset

	def paginate_queryset(self, queryset, view=None):
		if 'no_page' in self.request.query_params:
			return None
		return self.paginator.paginate_queryset(
			queryset, self.request, view=self)


class SubdomainsViewSet(viewsets.ModelViewSet):
	queryset = Subdomain.objects.none()
	serializer_class = SubdomainSerializer

	def get_queryset(self):
		req = self.request
		scan_id = req.query_params.get('scan_id')
		if scan_id:
			if 'only_screenshot' in self.request.query_params:
				return (
					Subdomain.objects
					.filter(scan_history__id=scan_id)
					.exclude(screenshot_path__isnull=True))
			return Subdomain.objects.filter(scan_history=scan_id)

	def paginate_queryset(self, queryset, view=None):
		if 'no_page' in self.request.query_params:
			return None
		return self.paginator.paginate_queryset(
			queryset, self.request, view=self)


class SubdomainChangesViewSet(viewsets.ModelViewSet):
	'''
		This viewset will return the Subdomain changes
		To get the new subdomains, we will look for ScanHistory with
		subdomain_discovery = True and the status of the last scan has to be
		successful and calculate difference
	'''
	queryset = Subdomain.objects.none()
	serializer_class = SubdomainChangesSerializer

	def get_queryset(self):
		req = self.request
		scan_id = req.query_params.get('scan_id')
		changes = req.query_params.get('changes')
		domain_id = ScanHistory.objects.filter(id=scan_id)[0].domain.id
		scan_history_query = (
			ScanHistory.objects
			.filter(domain=domain_id)
			.filter(tasks__overlap=['subdomain_discovery'])
			.filter(id__lte=scan_id)
			.exclude(Q(scan_status=-1) | Q(scan_status=1))
		)
		if scan_history_query.count() > 1:
			last_scan = scan_history_query.order_by('-start_scan_date')[1]
			scanned_host_q1 = (
				Subdomain.objects
				.filter(scan_history__id=scan_id)
				.values('name')
			)
			scanned_host_q2 = (
				Subdomain.objects
				.filter(scan_history__id=last_scan.id)
				.values('name')
			)
			added_subdomain = scanned_host_q1.difference(scanned_host_q2)
			removed_subdomains = scanned_host_q2.difference(scanned_host_q1)
			if changes == 'added':
				return (
					Subdomain.objects
					.filter(scan_history=scan_id)
					.filter(name__in=added_subdomain)
					.annotate(
						change=Value('added', output_field=CharField())
					)
				)
			elif changes == 'removed':
				return (
					Subdomain.objects
					.filter(scan_history=last_scan)
					.filter(name__in=removed_subdomains)
					.annotate(
						change=Value('removed', output_field=CharField())
					)
				)
			else:
				added_subdomain = (
					Subdomain.objects
					.filter(scan_history=scan_id)
					.filter(name__in=added_subdomain)
					.annotate(
						change=Value('added', output_field=CharField())
					)
				)
				removed_subdomains = (
					Subdomain.objects
					.filter(scan_history=last_scan)
					.filter(name__in=removed_subdomains)
					.annotate(
						change=Value('removed', output_field=CharField())
					)
				)
				changes = added_subdomain.union(removed_subdomains)
				return changes
		return self.queryset

	def paginate_queryset(self, queryset, view=None):
		if 'no_page' in self.request.query_params:
			return None
		return self.paginator.paginate_queryset(
			queryset, self.request, view=self)


class EndPointChangesViewSet(viewsets.ModelViewSet):
	'''
		This viewset will return the EndPoint changes
	'''
	queryset = EndPoint.objects.none()
	serializer_class = EndPointChangesSerializer

	def get_queryset(self):
		req = self.request
		scan_id = req.query_params.get('scan_id')
		changes = req.query_params.get('changes')
		domain_id = ScanHistory.objects.filter(id=scan_id).first().domain.id
		scan_history = (
			ScanHistory.objects
			.filter(domain=domain_id)
			.filter(tasks__overlap=['fetch_url'])
			.filter(id__lte=scan_id)
			.filter(scan_status=2)
		)
		if scan_history.count() > 1:
			last_scan = scan_history.order_by('-start_scan_date')[1]
			scanned_host_q1 = (
				EndPoint.objects
				.filter(scan_history__id=scan_id)
				.values('http_url')
			)
			scanned_host_q2 = (
				EndPoint.objects
				.filter(scan_history__id=last_scan.id)
				.values('http_url')
			)
			added_endpoints = scanned_host_q1.difference(scanned_host_q2)
			removed_endpoints = scanned_host_q2.difference(scanned_host_q1)
			if changes == 'added':
				return (
					EndPoint.objects
					.filter(scan_history=scan_id)
					.filter(http_url__in=added_endpoints)
					.annotate(change=Value('added', output_field=CharField()))
				)
			elif changes == 'removed':
				return (
					EndPoint.objects
					.filter(scan_history=last_scan)
					.filter(http_url__in=removed_endpoints)
					.annotate(change=Value('removed', output_field=CharField()))
				)
			else:
				added_endpoints = (
					EndPoint.objects
					.filter(scan_history=scan_id)
					.filter(http_url__in=added_endpoints)
					.annotate(change=Value('added', output_field=CharField()))
				)
				removed_endpoints = (
					EndPoint.objects
					.filter(scan_history=last_scan)
					.filter(http_url__in=removed_endpoints)
					.annotate(change=Value('removed', output_field=CharField()))
				)
				changes = added_endpoints.union(removed_endpoints)
				return changes
		return self.queryset

	def paginate_queryset(self, queryset, view=None):
		if 'no_page' in self.request.query_params:
			return None
		return self.paginator.paginate_queryset(
			queryset, self.request, view=self)


class InterestingSubdomainViewSet(viewsets.ModelViewSet):
	queryset = Subdomain.objects.none()
	serializer_class = SubdomainSerializer

	def get_queryset(self):
		req = self.request
		scan_id = req.query_params.get('scan_id')
		domain_id = req.query_params.get('target_id')

		if 'only_subdomains' in self.request.query_params:
			self.serializer_class = InterestingSubdomainSerializer

		if scan_id:
			self.queryset = get_interesting_subdomains(scan_history=scan_id)
		elif domain_id:
			self.queryset = get_interesting_subdomains(domain_id=domain_id)
		else:
			self.queryset = get_interesting_subdomains()

		return self.queryset

	def filter_queryset(self, qs):
		qs = self.queryset.filter()
		search_value = self.request.GET.get(u'search[value]', None)
		_order_col = self.request.GET.get(u'order[0][column]', None)
		_order_direction = self.request.GET.get(u'order[0][dir]', None)
		order_col = 'content_length'
		if _order_col == '0':
			order_col = 'name'
		elif _order_col == '1':
			order_col = 'page_title'
		elif _order_col == '2':
			order_col = 'http_status'
		elif _order_col == '3':
			order_col = 'content_length'

		if _order_direction == 'desc':
			order_col = '-{}'.format(order_col)

		if search_value:
			qs = self.queryset.filter(
				Q(name__icontains=search_value) |
				Q(page_title__icontains=search_value) |
				Q(http_status__icontains=search_value)
			)
		return qs.order_by(order_col)

	def paginate_queryset(self, queryset, view=None):
		if 'no_page' in self.request.query_params:
			return None
		return self.paginator.paginate_queryset(
			queryset, self.request, view=self)


class InterestingEndpointViewSet(viewsets.ModelViewSet):
	queryset = EndPoint.objects.none()
	serializer_class = EndpointSerializer

	def get_queryset(self):
		req = self.request
		scan_id = req.query_params.get('scan_id')
		target_id = req.query_params.get('target_id')
		if 'only_endpoints' in self.request.query_params:
			self.serializer_class = InterestingEndPointSerializer
		if scan_id:
			return get_interesting_endpoints(scan_history=scan_id)
		elif target_id:
			return get_interesting_endpoints(target=target_id)
		else:
			return get_interesting_endpoints()

	def paginate_queryset(self, queryset, view=None):
		if 'no_page' in self.request.query_params:
			return None
		return self.paginator.paginate_queryset(
			queryset, self.request, view=self)


class SubdomainDatatableViewSet(viewsets.ModelViewSet):
	queryset = Subdomain.objects.none()
	serializer_class = SubdomainSerializer

	def get_queryset(self):
		req = self.request
		scan_id = req.query_params.get('scan_id')
		target_id = req.query_params.get('target_id')
		url_query = req.query_params.get('query_param')
		ip_address = req.query_params.get('ip_address')
		name = req.query_params.get('name')
		project = req.query_params.get('project')

		subdomains = Subdomain.objects.filter(target_domain__project__slug=project)

		if target_id:
			self.queryset = (
				subdomains
				.filter(target_domain__id=target_id)
				.distinct()
			)
		elif url_query:
			self.queryset = (
				subdomains
				.filter(Q(target_domain__name=url_query))
				.distinct()
			)
		elif scan_id:
			self.queryset = (
				subdomains
				.filter(scan_history__id=scan_id)
				.distinct()
			)
		else:
			self.queryset = subdomains.distinct()

		if 'only_directory' in req.query_params:
			self.queryset = self.queryset.exclude(directories__isnull=True)

		if ip_address:
			self.queryset = self.queryset.filter(ip_addresses__address__icontains=ip_address)

		if name:
			self.queryset = self.queryset.filter(name=name)

		return self.queryset

	def filter_queryset(self, qs):
		qs = self.queryset.filter()
		search_value = self.request.GET.get(u'search[value]', None)
		_order_col = self.request.GET.get(u'order[0][column]', None)
		_order_direction = self.request.GET.get(u'order[0][dir]', None)
		order_col = 'content_length'
		if _order_col == '0':
			order_col = 'checked'
		elif _order_col == '1':
			order_col = 'name'
		elif _order_col == '4':
			order_col = 'http_status'
		elif _order_col == '5':
			order_col = 'page_title'
		elif _order_col == '8':
			order_col = 'content_length'
		elif _order_col == '10':
			order_col = 'response_time'
		if _order_direction == 'desc':
			order_col = '-{}'.format(order_col)
		# if the search query is separated by = means, it is a specific lookup
		# divide the search query into two half and lookup
		if search_value:
			operators = ['=', '&', '|', '>', '<', '!']
			if any(x in search_value for x in operators):
				if '&' in search_value:
					complex_query = search_value.split('&')
					for query in complex_query:
						if query.strip():
							qs = qs & self.special_lookup(query.strip())
				elif '|' in search_value:
					qs = Subdomain.objects.none()
					complex_query = search_value.split('|')
					for query in complex_query:
						if query.strip():
							qs = self.special_lookup(query.strip()) | qs
				else:
					qs = self.special_lookup(search_value)
			else:
				qs = self.general_lookup(search_value)
		return qs.order_by(order_col)

	def general_lookup(self, search_value):
		qs = self.queryset.filter(
			Q(name__icontains=search_value) |
			Q(cname__icontains=search_value) |
			Q(http_status__icontains=search_value) |
			Q(page_title__icontains=search_value) |
			Q(http_url__icontains=search_value) |
			Q(technologies__name__icontains=search_value) |
			Q(webserver__icontains=search_value) |
			Q(ip_addresses__address__icontains=search_value) |
			Q(ip_addresses__ports__number__icontains=search_value) |
			Q(ip_addresses__ports__service_name__icontains=search_value) |
			Q(ip_addresses__ports__description__icontains=search_value)
		)

		if 'only_directory' in self.request.query_params:
			qs = qs | self.queryset.filter(
				Q(directories__directory_files__name__icontains=search_value)
			)

		return qs

	def special_lookup(self, search_value):
		qs = self.queryset.filter()
		if '=' in search_value:
			search_param = search_value.split("=")
			title = search_param[0].lower().strip()
			content = search_param[1].lower().strip()
			if 'name' in title:
				qs = self.queryset.filter(name__icontains=content)
			elif 'page_title' in title:
				qs = self.queryset.filter(page_title__icontains=content)
			elif 'http_url' in title:
				qs = self.queryset.filter(http_url__icontains=content)
			elif 'content_type' in title:
				qs = self.queryset.filter(content_type__icontains=content)
			elif 'cname' in title:
				qs = self.queryset.filter(cname__icontains=content)
			elif 'webserver' in title:
				qs = self.queryset.filter(webserver__icontains=content)
			elif 'ip_addresses' in title:
				qs = self.queryset.filter(
					ip_addresses__address__icontains=content)
			elif 'is_important' in title:
				if 'true' in content.lower():
					qs = self.queryset.filter(is_important=True)
				else:
					qs = self.queryset.filter(is_important=False)
			elif 'port' in title:
				qs = (
					self.queryset
					.filter(ip_addresses__ports__number__icontains=content)
					|
					self.queryset
					.filter(ip_addresses__ports__service_name__icontains=content)
					|
					self.queryset
					.filter(ip_addresses__ports__description__icontains=content)
				)
			elif 'technology' in title:
				qs = (
					self.queryset
					.filter(technologies__name__icontains=content)
				)
			elif 'http_status' in title:
				try:
					int_http_status = int(content)
					qs = self.queryset.filter(http_status=int_http_status)
				except Exception as e:
					print(e)
			elif 'content_length' in title:
				try:
					int_http_status = int(content)
					qs = self.queryset.filter(content_length=int_http_status)
				except Exception as e:
					print(e)

		elif '>' in search_value:
			search_param = search_value.split(">")
			title = search_param[0].lower().strip()
			content = search_param[1].lower().strip()
			if 'http_status' in title:
				try:
					int_val = int(content)
					qs = self.queryset.filter(http_status__gt=int_val)
				except Exception as e:
					print(e)
			elif 'content_length' in title:
				try:
					int_val = int(content)
					qs = self.queryset.filter(content_length__gt=int_val)
				except Exception as e:
					print(e)

		elif '<' in search_value:
			search_param = search_value.split("<")
			title = search_param[0].lower().strip()
			content = search_param[1].lower().strip()
			if 'http_status' in title:
				try:
					int_val = int(content)
					qs = self.queryset.filter(http_status__lt=int_val)
				except Exception as e:
					print(e)
			elif 'content_length' in title:
				try:
					int_val = int(content)
					qs = self.queryset.filter(content_length__lt=int_val)
				except Exception as e:
					print(e)

		elif '!' in search_value:
			search_param = search_value.split("!")
			title = search_param[0].lower().strip()
			content = search_param[1].lower().strip()
			if 'name' in title:
				qs = self.queryset.exclude(name__icontains=content)
			elif 'page_title' in title:
				qs = self.queryset.exclude(page_title__icontains=content)
			elif 'http_url' in title:
				qs = self.queryset.exclude(http_url__icontains=content)
			elif 'content_type' in title:
				qs = (
					self.queryset
					.exclude(content_type__icontains=content)
				)
			elif 'cname' in title:
				qs = self.queryset.exclude(cname__icontains=content)
			elif 'webserver' in title:
				qs = self.queryset.exclude(webserver__icontains=content)
			elif 'ip_addresses' in title:
				qs = self.queryset.exclude(
					ip_addresses__address__icontains=content)
			elif 'port' in title:
				qs = (
					self.queryset
					.exclude(ip_addresses__ports__number__icontains=content)
					|
					self.queryset
					.exclude(ip_addresses__ports__service_name__icontains=content)
					|
					self.queryset
					.exclude(ip_addresses__ports__description__icontains=content)
				)
			elif 'technology' in title:
				qs = (
					self.queryset
					.exclude(technologies__name__icontains=content)
				)
			elif 'http_status' in title:
				try:
					int_http_status = int(content)
					qs = self.queryset.exclude(http_status=int_http_status)
				except Exception as e:
					print(e)
			elif 'content_length' in title:
				try:
					int_http_status = int(content)
					qs = self.queryset.exclude(content_length=int_http_status)
				except Exception as e:
					print(e)

		return qs


class ListActivityLogsViewSet(viewsets.ModelViewSet):
	serializer_class = CommandSerializer
	queryset = Command.objects.none()
	def get_queryset(self):
		req = self.request
		activity_id = req.query_params.get('activity_id')
		self.queryset = Command.objects.filter(activity__id=activity_id)
		return self.queryset


class ListScanLogsViewSet(viewsets.ModelViewSet):
	serializer_class = CommandSerializer
	queryset = Command.objects.none()
	def get_queryset(self):
		req = self.request
		scan_id = req.query_params.get('scan_id')
		self.queryset = Command.objects.filter(scan_history__id=scan_id)
		return self.queryset


class ListEndpoints(APIView):
	def get(self, request, format=None):
		req = self.request

		scan_id = req.query_params.get('scan_id')
		target_id = req.query_params.get('target_id')
		subdomain_name = req.query_params.get('subdomain_name')
		pattern = req.query_params.get('pattern')

		if scan_id:
			endpoints = (
				EndPoint.objects
				.filter(scan_history__id=scan_id)
			)
		elif target_id:
			endpoints = (
				EndPoint.objects
				.filter(target_domain__id=target_id)
				.distinct()
			)
		else:
			endpoints = EndPoint.objects.all()

		if subdomain_name:
			endpoints = endpoints.filter(subdomain__name=subdomain_name)

		if pattern:
			endpoints = endpoints.filter(matched_gf_patterns__icontains=pattern)

		if 'only_urls' in req.query_params:
			endpoints_serializer = EndpointOnlyURLsSerializer(endpoints, many=True)

		else:
			endpoints_serializer = EndpointSerializer(endpoints, many=True)

		return Response({'endpoints': endpoints_serializer.data})


class EndPointViewSet(viewsets.ModelViewSet):
	queryset = EndPoint.objects.none()
	serializer_class = EndpointSerializer

	def get_queryset(self):
		req = self.request

		scan_id = req.query_params.get('scan_history')
		target_id = req.query_params.get('target_id')
		url_query = req.query_params.get('query_param')
		subdomain_id = req.query_params.get('subdomain_id')
		project = req.query_params.get('project')

		endpoints_obj = EndPoint.objects.filter(scan_history__domain__project__slug=project)

		gf_tag = req.query_params.get(
			'gf_tag') if 'gf_tag' in req.query_params else None

		if scan_id:
			endpoints = (
				endpoints_obj
				.filter(scan_history__id=scan_id)
				.distinct()
			)
		else:
			endpoints = endpoints_obj.distinct()

		if url_query:
			endpoints = (
				endpoints
				.filter(Q(target_domain__name=url_query))
				.distinct()
			)

		if gf_tag:
			endpoints = endpoints.filter(matched_gf_patterns__icontains=gf_tag)

		if target_id:
			endpoints = endpoints.filter(target_domain__id=target_id)

		if subdomain_id:
			endpoints = endpoints.filter(subdomain__id=subdomain_id)

		if 'only_urls' in req.query_params:
			self.serializer_class = EndpointOnlyURLsSerializer

		# Filter status code 404 and 0
		# endpoints = (
		# 	endpoints
		# 	.exclude(http_status=0)
		# 	.exclude(http_status=None)
		# 	.exclude(http_status=404)
		# )

		self.queryset = endpoints

		return self.queryset

	def filter_queryset(self, qs):
		qs = self.queryset.filter()
		search_value = self.request.GET.get(u'search[value]', None)
		_order_col = self.request.GET.get(u'order[0][column]', None)
		_order_direction = self.request.GET.get(u'order[0][dir]', None)
		if search_value or _order_col or _order_direction:
			order_col = 'content_length'
			if _order_col == '1':
				order_col = 'http_url'
			elif _order_col == '2':
				order_col = 'http_status'
			elif _order_col == '3':
				order_col = 'page_title'
			elif _order_col == '4':
				order_col = 'matched_gf_patterns'
			elif _order_col == '5':
				order_col = 'content_type'
			elif _order_col == '6':
				order_col = 'content_length'
			elif _order_col == '7':
				order_col = 'techs'
			elif _order_col == '8':
				order_col = 'webserver'
			elif _order_col == '9':
				order_col = 'response_time'
			if _order_direction == 'desc':
				order_col = '-{}'.format(order_col)
			# if the search query is separated by = means, it is a specific lookup
			# divide the search query into two half and lookup
			if '=' in search_value or '&' in search_value or '|' in search_value or '>' in search_value or '<' in search_value or '!' in search_value:
				if '&' in search_value:
					complex_query = search_value.split('&')
					for query in complex_query:
						if query.strip():
							qs = qs & self.special_lookup(query.strip())
				elif '|' in search_value:
					qs = Subdomain.objects.none()
					complex_query = search_value.split('|')
					for query in complex_query:
						if query.strip():
							qs = self.special_lookup(query.strip()) | qs
				else:
					qs = self.special_lookup(search_value)
			else:
				qs = self.general_lookup(search_value)
			return qs.order_by(order_col)
		return qs

	def general_lookup(self, search_value):
		return \
			self.queryset.filter(Q(http_url__icontains=search_value) |
								 Q(page_title__icontains=search_value) |
								 Q(http_status__icontains=search_value) |
								 Q(content_type__icontains=search_value) |
								 Q(webserver__icontains=search_value) |
								 Q(techs__name__icontains=search_value) |
								 Q(content_type__icontains=search_value) |
								 Q(matched_gf_patterns__icontains=search_value))

	def special_lookup(self, search_value):
		qs = self.queryset.filter()
		if '=' in search_value:
			search_param = search_value.split("=")
			lookup_title = search_param[0].lower().strip()
			lookup_content = search_param[1].lower().strip()
			if 'http_url' in lookup_title:
				qs = self.queryset.filter(http_url__icontains=lookup_content)
			elif 'page_title' in lookup_title:
				qs = (
					self.queryset
					.filter(page_title__icontains=lookup_content)
				)
			elif 'content_type' in lookup_title:
				qs = (
					self.queryset
					.filter(content_type__icontains=lookup_content)
				)
			elif 'webserver' in lookup_title:
				qs = self.queryset.filter(webserver__icontains=lookup_content)
			elif 'technology' in lookup_title:
				qs = (
					self.queryset
					.filter(techs__name__icontains=lookup_content)
				)
			elif 'gf_pattern' in lookup_title:
				qs = (
					self.queryset
					.filter(matched_gf_patterns__icontains=lookup_content)
				)
			elif 'http_status' in lookup_title:
				try:
					int_http_status = int(lookup_content)
					qs = self.queryset.filter(http_status=int_http_status)
				except Exception as e:
					print(e)
			elif 'content_length' in lookup_title:
				try:
					int_http_status = int(lookup_content)
					qs = self.queryset.filter(content_length=int_http_status)
				except Exception as e:
					print(e)
		elif '>' in search_value:
			search_param = search_value.split(">")
			lookup_title = search_param[0].lower().strip()
			lookup_content = search_param[1].lower().strip()
			if 'http_status' in lookup_title:
				try:
					int_val = int(lookup_content)
					qs = (
						self.queryset
						.filter(http_status__gt=int_val)
					)
				except Exception as e:
					print(e)
			elif 'content_length' in lookup_title:
				try:
					int_val = int(lookup_content)
					qs = self.queryset.filter(content_length__gt=int_val)
				except Exception as e:
					print(e)
		elif '<' in search_value:
			search_param = search_value.split("<")
			lookup_title = search_param[0].lower().strip()
			lookup_content = search_param[1].lower().strip()
			if 'http_status' in lookup_title:
				try:
					int_val = int(lookup_content)
					qs = self.queryset.filter(http_status__lt=int_val)
				except Exception as e:
					print(e)
			elif 'content_length' in lookup_title:
				try:
					int_val = int(lookup_content)
					qs = self.queryset.filter(content_length__lt=int_val)
				except Exception as e:
					print(e)
		elif '!' in search_value:
			search_param = search_value.split("!")
			lookup_title = search_param[0].lower().strip()
			lookup_content = search_param[1].lower().strip()
			if 'http_url' in lookup_title:
				qs = (
					self.queryset
					.exclude(http_url__icontains=lookup_content)
				)
			elif 'page_title' in lookup_title:
				qs = (
					self.queryset
					.exclude(page_title__icontains=lookup_content)
				)
			elif 'content_type' in lookup_title:
				qs = (
					self.queryset
					.exclude(content_type__icontains=lookup_content)
				)
			elif 'webserver' in lookup_title:
				qs = (
					self.queryset
					.exclude(webserver__icontains=lookup_content)
				)
			elif 'technology' in lookup_title:
				qs = (
					self.queryset
					.exclude(techs__name__icontains=lookup_content)
				)
			elif 'gf_pattern' in lookup_title:
				qs = (
					self.queryset
					.exclude(matched_gf_patterns__icontains=lookup_content)
				)
			elif 'http_status' in lookup_title:
				try:
					int_http_status = int(lookup_content)
					qs = self.queryset.exclude(http_status=int_http_status)
				except Exception as e:
					print(e)
			elif 'content_length' in lookup_title:
				try:
					int_http_status = int(lookup_content)
					qs = self.queryset.exclude(content_length=int_http_status)
				except Exception as e:
					print(e)
		return qs


class DirectoryViewSet(viewsets.ModelViewSet):
	queryset = DirectoryFile.objects.none()
	serializer_class = DirectoryFileSerializer

	def get_queryset(self):
		req = self.request
		scan_id = req.query_params.get('scan_history')
		subdomain_id = req.query_params.get('subdomain_id')
		subdomains = None
		if not (scan_id or subdomain_id):
			return Response({
				'status': False,
				'message': 'Scan id or subdomain id must be provided.'
			})
		elif scan_id:
			subdomains = Subdomain.objects.filter(scan_history__id=scan_id)
		elif subdomain_id:
			subdomains = Subdomain.objects.filter(id=subdomain_id)
		dirs_scans = DirectoryScan.objects.filter(directories__in=subdomains)
		qs = (
			DirectoryFile.objects
			.filter(directory_files__in=dirs_scans)
			.distinct()
		)
		self.queryset = qs
		return self.queryset


class VulnerabilityViewSet(viewsets.ModelViewSet):
	queryset = Vulnerability.objects.none()
	serializer_class = VulnerabilitySerializer

	def get_queryset(self):
		req = self.request
		scan_id = req.query_params.get('scan_history')
		target_id = req.query_params.get('target_id')
		domain = req.query_params.get('domain')
		severity = req.query_params.get('severity')
		subdomain_id = req.query_params.get('subdomain_id')
		subdomain_name = req.query_params.get('subdomain')
		vulnerability_name = req.query_params.get('vulnerability_name')
		slug = self.request.GET.get('project', None)

		if slug:
			vulnerabilities = Vulnerability.objects.filter(scan_history__domain__project__slug=slug)
		else:
			vulnerabilities = Vulnerability.objects.all()

		if scan_id:
			qs = (
				vulnerabilities
				.filter(scan_history__id=scan_id)
				.distinct()
			)
		elif target_id:
			qs = (
				vulnerabilities
				.filter(target_domain__id=target_id)
				.distinct()
			)
		elif subdomain_name:
			subdomains = Subdomain.objects.filter(name=subdomain_name)
			qs = (
				vulnerabilities
				.filter(subdomain__in=subdomains)
				.distinct()
			)
		else:
			qs = vulnerabilities.distinct()

		if domain:
			qs = qs.filter(Q(target_domain__name=domain)).distinct()
		if vulnerability_name:
			qs = qs.filter(Q(name=vulnerability_name)).distinct()
		if severity:
			qs = qs.filter(severity=severity)
		if subdomain_id:
			qs = qs.filter(subdomain__id=subdomain_id)
		self.queryset = qs
		return self.queryset

	def filter_queryset(self, qs):
		qs = self.queryset.filter()
		search_value = self.request.GET.get(u'search[value]', None)
		_order_col = self.request.GET.get(u'order[0][column]', None)
		_order_direction = self.request.GET.get(u'order[0][dir]', None)
		if search_value or _order_col or _order_direction:
			order_col = 'severity'
			if _order_col == '1':
				order_col = 'source'
			elif _order_col == '3':
				order_col = 'name'
			elif _order_col == '7':
				order_col = 'severity'
			elif _order_col == '11':
				order_col = 'http_url'
			elif _order_col == '15':
				order_col = 'open_status'

			if _order_direction == 'desc':
				order_col = f'-{order_col}'
			# if the search query is separated by = means, it is a specific lookup
			# divide the search query into two half and lookup
			operators = ['=', '&', '|', '>', '<', '!']
			if any(x in search_value for x in operators):
				if '&' in search_value:
					complex_query = search_value.split('&')
					for query in complex_query:
						if query.strip():
							qs = qs & self.special_lookup(query.strip())
				elif '|' in search_value:
					qs = Subdomain.objects.none()
					complex_query = search_value.split('|')
					for query in complex_query:
						if query.strip():
							qs = self.special_lookup(query.strip()) | qs
				else:
					qs = self.special_lookup(search_value)
			else:
				qs = self.general_lookup(search_value)
			return qs.order_by(order_col)
		return qs.order_by('-severity')

	def general_lookup(self, search_value):
		qs = (
			self.queryset
			.filter(Q(http_url__icontains=search_value) |
					Q(target_domain__name__icontains=search_value) |
					Q(template__icontains=search_value) |
					Q(template_id__icontains=search_value) |
					Q(name__icontains=search_value) |
					Q(severity__icontains=search_value) |
					Q(description__icontains=search_value) |
					Q(extracted_results__icontains=search_value) |
					Q(references__url__icontains=search_value) |
					Q(cve_ids__name__icontains=search_value) |
					Q(cwe_ids__name__icontains=search_value) |
					Q(cvss_metrics__icontains=search_value) |
					Q(cvss_score__icontains=search_value) |
					Q(type__icontains=search_value) |
					Q(open_status__icontains=search_value) |
					Q(hackerone_report_id__icontains=search_value) |
					Q(tags__name__icontains=search_value))
		)
		return qs

	def special_lookup(self, search_value):
		qs = self.queryset.filter()
		if '=' in search_value:
			search_param = search_value.split("=")
			lookup_title = search_param[0].lower().strip()
			lookup_content = search_param[1].lower().strip()
			if 'severity' in lookup_title:
				severity_value = NUCLEI_SEVERITY_MAP.get(lookup_content, -1)
				qs = (
					self.queryset
					.filter(severity=severity_value)
				)
			elif 'name' in lookup_title:
				qs = (
					self.queryset
					.filter(name__icontains=lookup_content)
				)
			elif 'http_url' in lookup_title:
				qs = (
					self.queryset
					.filter(http_url__icontains=lookup_content)
				)
			elif 'template' in lookup_title:
				qs = (
					self.queryset
					.filter(template__icontains=lookup_content)
				)
			elif 'template_id' in lookup_title:
				qs = (
					self.queryset
					.filter(template_id__icontains=lookup_content)
				)
			elif 'cve_id' in lookup_title or 'cve' in lookup_title:
				qs = (
					self.queryset
					.filter(cve_ids__name__icontains=lookup_content)
				)
			elif 'cwe_id' in lookup_title or 'cwe' in lookup_title:
				qs = (
					self.queryset
					.filter(cwe_ids__name__icontains=lookup_content)
				)
			elif 'cvss_metrics' in lookup_title:
				qs = (
					self.queryset
					.filter(cvss_metrics__icontains=lookup_content)
				)
			elif 'cvss_score' in lookup_title:
				qs = (
					self.queryset
					.filter(cvss_score__exact=lookup_content)
				)
			elif 'type' in lookup_title:
				qs = (
					self.queryset
					.filter(type__icontains=lookup_content)
				)
			elif 'tag' in lookup_title:
				qs = (
					self.queryset
					.filter(tags__name__icontains=lookup_content)
				)
			elif 'status' in lookup_title:
				open_status = lookup_content == 'open'
				qs = (
					self.queryset
					.filter(open_status=open_status)
				)
			elif 'description' in lookup_title:
				qs = (
					self.queryset
					.filter(Q(description__icontains=lookup_content) |
							Q(template__icontains=lookup_content) |
							Q(extracted_results__icontains=lookup_content))
				)
		elif '!' in search_value:
			search_param = search_value.split("!")
			lookup_title = search_param[0].lower().strip()
			lookup_content = search_param[1].lower().strip()
			if 'severity' in lookup_title:
				severity_value = NUCLEI_SEVERITY_MAP.get(lookup_title, -1)
				qs = (
					self.queryset
					.exclude(severity=severity_value)
				)
			elif 'name' in lookup_title:
				qs = (
					self.queryset
					.exclude(name__icontains=lookup_content)
				)
			elif 'http_url' in lookup_title:
				qs = (
					self.queryset
					.exclude(http_url__icontains=lookup_content)
				)
			elif 'template' in lookup_title:
				qs = (
					self.queryset
					.exclude(template__icontains=lookup_content)
				)
			elif 'template_id' in lookup_title:
				qs = (
					self.queryset
					.exclude(template_id__icontains=lookup_content)
				)
			elif 'cve_id' in lookup_title or 'cve' in lookup_title:
				qs = (
					self.queryset
					.exclude(cve_ids__icontains=lookup_content)
				)
			elif 'cwe_id' in lookup_title or 'cwe' in lookup_title:
				qs = (
					self.queryset
					.exclude(cwe_ids__icontains=lookup_content)
				)
			elif 'cvss_metrics' in lookup_title:
				qs = (
					self.queryset
					.exclude(cvss_metrics__icontains=lookup_content)
				)
			elif 'cvss_score' in lookup_title:
				qs = (
					self.queryset
					.exclude(cvss_score__exact=lookup_content)
				)
			elif 'type' in lookup_title:
				qs = (
					self.queryset
					.exclude(type__icontains=lookup_content)
				)
			elif 'tag' in lookup_title:
				qs = (
					self.queryset
					.exclude(tags__icontains=lookup_content)
				)
			elif 'status' in lookup_title:
				open_status = lookup_content == 'open'
				qs = (
					self.queryset
					.exclude(open_status=open_status)
				)
			elif 'description' in lookup_title:
				qs = (
					self.queryset
					.exclude(Q(description__icontains=lookup_content) |
							 Q(template__icontains=lookup_content) |
							 Q(extracted_results__icontains=lookup_content))
				)

		elif '>' in search_value:
			search_param = search_value.split(">")
			lookup_title = search_param[0].lower().strip()
			lookup_content = search_param[1].lower().strip()
			if 'cvss_score' in lookup_title:
				try:
					val = float(lookup_content)
					qs = self.queryset.filter(cvss_score__gt=val)
				except Exception as e:
					print(e)

		elif '<' in search_value:
			search_param = search_value.split("<")
			lookup_title = search_param[0].lower().strip()
			lookup_content = search_param[1].lower().strip()
			if 'cvss_score' in lookup_title:
				try:
					val = int(lookup_content)
					qs = self.queryset.filter(cvss_score__lt=val)
				except Exception as e:
					print(e)

		return qs

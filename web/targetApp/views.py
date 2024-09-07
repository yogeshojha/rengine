import csv
import io
import logging
import validators

from datetime import timedelta
from urllib.parse import urlparse
from django import http
from django.conf import settings
from django.contrib import messages
from django.db.models import Count
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.utils.safestring import mark_safe
from rolepermissions.decorators import has_permission_decorator

from reNgine.common_func import *
from reNgine.tasks import run_command, sanitize_url
from scanEngine.models import *
from startScan.models import *
from targetApp.forms import *
from targetApp.models import *

logger = logging.getLogger(__name__)


def index(request):
    # TODO bring default target page
    return render(request, 'target/index.html')


@has_permission_decorator(PERM_MODIFY_TARGETS, redirect_url=FOUR_OH_FOUR_URL)
def add_target(request, slug):
    """Add a new target. Targets can be URLs, IPs, CIDR ranges, or Domains.

    Args:
        request: Django request.
    """
    project = Project.objects.get(slug=slug)
    form = AddTargetForm(request.POST or None)
    if request.method == "POST":
        logger.info(request.POST)
        added_target_count = 0
        multiple_targets = request.POST.get('add-multiple-targets')
        ip_target = request.POST.get('add-ip-target')
        try:
            # Multiple targets
            if multiple_targets:
                bulk_targets = [t.rstrip() for t in request.POST['addTargets'].split('\n') if t]
                logger.info(f'Adding multiple targets: {bulk_targets}')
                description = request.POST.get('targetDescription', '')
                h1_team_handle = request.POST.get('targetH1TeamHandle', '')
                organization_name = request.POST.get('targetOrganization')
                for target in bulk_targets:
                    target = target.rstrip('\n')
                    http_urls = []
                    domains = []
                    ports = []
                    ips = []

                    # Validate input and find what type of address it is.
                    # Valid inputs are URLs, Domains, or IP addresses.
                    # TODO: support IP CIDR ranges (auto expand range and
                    # save new found ips to DB)
                    is_domain = bool(validators.domain(target))
                    is_ip = bool(validators.ipv4(target)) or bool(validators.ipv6(target))
                    is_range = bool(validators.ipv4_cidr(target)) or bool(validators.ipv6_cidr(target))
                    is_url = bool(validators.url(target))

                    # Set ip_domain / http_url based on type of input
                    logger.info(f'{target} | Domain? {is_domain} | IP? {is_ip} | CIDR range? {is_range} | URL? {is_url}')

                    if is_domain:
                       domains.append(target)

                    elif is_url:
                        url = urlparse(target)
                        http_url = url.geturl()
                        http_urls.append(http_url)
                        split = url.netloc.split(':')
                        if len(split) == 1:
                            domain = split[0]
                            domains.append(domain)
                        if len(split) == 2:
                            domain, port_number = tuple(split)
                            domains.append(domain)
                            ports.append(port_number)

                    elif is_ip:
                        ips.append(target)
                        domains.append(target)

                    elif is_range:
                        _ips = get_ips_from_cidr_range(target)
                        for ip_address in _ips:
                            ips.append(ip_address)
                            domains.append(ip_address)
                    else:
                        msg = f'{target} is not a valid domain, IP, or URL. Skipped.'
                        logger.warning(msg)
                        messages.add_message(
                            request,
                            messages.WARNING,
                            msg)
                        continue

                    logger.info(f'IPs: {ips} | Domains: {domains} | URLs: {http_urls} | Ports: {ports}')

                    for domain_name in domains:
                        if not Domain.objects.filter(name=domain_name).exists():
                            domain, created = Domain.objects.get_or_create(
                                name=domain_name,
                                description=description,
                                h1_team_handle=h1_team_handle,
                                project=project,
                                ip_address_cidr=domain_name if is_ip else None)
                            domain.insert_date = timezone.now()
                            domain.save()
                            added_target_count += 1
                            if created:
                                logger.info(f'Added new domain {domain.name}')

                            if organization_name:
                                organization = None
                                if Organization.objects.filter(name=organization_name).exists():
                                    organization = organization_query[0]
                                else:
                                    organization = Organization.objects.create(
                                        name=organization_name,
                                        project=project,
                                        insert_date=timezone.now())
                                organization.domains.add(domain)


                    for http_url in http_urls:
                        http_url = sanitize_url(http_url)
                        endpoint, created = EndPoint.objects.get_or_create(
                            target_domain=domain,
                            http_url=http_url)
                        if created:
                            logger.info(f'Added new endpoint {endpoint.http_url}')

                    for ip_address in ips:
                        ip_data = get_ip_info(ip_address)
                        ip, created = IpAddress.objects.get_or_create(address=ip_address)
                        ip.reverse_pointer = ip_data.reverse_pointer
                        ip.is_private = ip_data.is_private
                        ip.version = ip_data.version
                        ip.save()
                        if created:
                            logger.warning(f'Added new IP {ip}')

                    for port_number in ports:
                        res = get_port_service_description(port_number)
                        port, created = update_or_create_port(
                            port_number=port_number,
                            service_name=res.get('service_name', ''),
                            description=res.get('description', '')
                        )
                        if created:
                            logger.warning(f'Added new port {port_number} to DB')

            # Import from txt / csv
            elif 'import-txt-target' in request.POST or 'import-csv-target' in request.POST:
                txt_file = request.FILES.get('txtFile')
                csv_file = request.FILES.get('csvFile')
                if not (txt_file or csv_file):
                    messages.add_message(
                        request,
                        messages.ERROR,
                        'Files uploaded are not .txt or .csv files.')
                    return http.HttpResponseRedirect(reverse('add_target', kwargs={'slug': slug}))

                #Specters Fix
                if txt_file:
                    is_txt = txt_file.content_type == 'text/plain' or txt_file.name.split('.')[-1] == 'txt'
                    if not is_txt:
                        messages.add_message(
                            request,
                            messages.ERROR,
                            'File is not a valid TXT file')
                        return http.HttpResponseRedirect(reverse('add_target', kwargs={'slug': slug}))
                    txt_content = txt_file.read().decode('UTF-8')
                    io_string = io.StringIO(txt_content)
                    for target in io_string:
                        target_domain = target.rstrip("\n").rstrip("\r")
                        domain = None  # Move the domain variable declaration here
                        domain_query = Domain.objects.filter(name=target_domain)
                        if not domain_query.exists():
                            if not validators.domain(target_domain):  # Change 'domain' to 'target_domain'
                                messages.add_message(request, messages.ERROR, f'Domain {target_domain} is not a valid domain name. Skipping.')
                                continue
                            Domain.objects.create(
                                name=target_domain,
                                project=project,
                                insert_date=timezone.now())
                            added_target_count += 1

                elif csv_file:
                    is_csv = csv_file.content_type = 'text/csv' or csv_file.name.split('.')[-1] == 'csv'
                    if not is_csv:
                        messages.add_message(
                            request,
                            messages.ERROR,
                            'File is not a valid CSV file.'
                        )
                        return http.HttpResponseRedirect(reverse('add_target', kwargs={'slug': slug}))
                    csv_content = csv_file.read().decode('UTF-8')
                    io_string = io.StringIO(csv_content)
                    for column in csv.reader(io_string, delimiter=','):
                        domain = column[0]
                        description = None if len(column) <= 1 else column[1]
                        organization = None if len(column) <= 2 else column[2]
                        domain_query = Domain.objects.filter(name=domain)
                        if not domain_query.exists():
                            if not validators.domain(domain):
                                messages.add_message(request, messages.ERROR, f'Domain {domain} is not a valid domain name. Skipping.')
                                continue
                            domain_obj = Domain.objects.create(
                                name=domain,
                                project=project,
                                description=description,
                                insert_date=timezone.now())
                            added_target_count += 1
                        
                            # Optionally add domain to organization
                            if organization:
                                organization_query = Organization.objects.filter(name=organization)
                                if organization_query.exists():
                                    organization = organization_query[0]
                                else:
                                    organization = Organization.objects.create(
                                        name=organization,
                                        project=project,
                                        insert_date=timezone.now())
                                organization.domains.add(domain_obj)
            elif ip_target:
                # add ip's from "resolve and add ip address" tab
                resolved_ips = [ip.rstrip() for ip in request.POST.getlist('resolved_ip_domains') if ip]
                for ip in resolved_ips:
                    is_domain = bool(validators.domain(ip))
                    is_ip = bool(validators.ipv4(ip)) or bool(validators.ipv6(ip))
                    description = request.POST.get('targetDescription', '')
                    h1_team_handle = request.POST.get('targetH1TeamHandle', '')
                    if not Domain.objects.filter(name=ip).exists():
                        domain, created = Domain.objects.get_or_create(
                            name=ip,
                            description=description,
                            h1_team_handle=h1_team_handle,
                            project=project,
                            ip_address_cidr=ip if is_ip else None)
                        domain.insert_date = timezone.now()
                        domain.save()
                        added_target_count += 1
                        if created:
                            logger.info(f'Added new domain {domain.name}')
                        if is_ip:
                            ip_data = get_ip_info(ip)
                            ip, created = IpAddress.objects.get_or_create(address=ip)
                            ip.reverse_pointer = ip_data.reverse_pointer
                            ip.is_private = ip_data.is_private
                            ip.version = ip_data.version
                            ip.save()
                            if created:
                                logger.info(f'Added new IP {ip}')

        except Exception as e:
            logger.exception(e)
            messages.add_message(
                request,
                messages.ERROR,
                f'Exception while adding domain: {e}'
            )
            return http.HttpResponseRedirect(reverse('add_target', kwargs={'slug': slug}))

        # No targets added, redirect to add target page
        if added_target_count == 0:
            messages.add_message(
                request,
                messages.ERROR,
                'Oops! Could not import any targets, either targets already exists or is not a valid target.')
            return http.HttpResponseRedirect(reverse('add_target', kwargs={'slug': slug}))

        # Targets added successfully, redirect to targets list
        msg = f'{added_target_count} targets added successfully'
        messages.add_message(request, messages.SUCCESS, msg)
        return http.HttpResponseRedirect(reverse('list_target', kwargs={'slug': slug}))

    # GET request
    context = {
        "add_target_li": "active",
        "target_data_active": "active",
        'form': form
    }
    return render(request, 'target/add.html', context)


def list_target(request, slug):
    context = {
        'list_target_li': 'active',
        'target_data_active': 'active',
        'slug': slug
    }
    return render(request, 'target/list.html', context)


@has_permission_decorator(PERM_MODIFY_TARGETS, redirect_url=FOUR_OH_FOUR_URL)
def delete_target(request, id):
    obj = get_object_or_404(Domain, id=id)
    if request.method == "POST":
        run_command(f'rm -rf {settings.TOOL_LOCATION} scan_results/{obj.name}*')
        obj.delete()
        responseData = {'status': 'true'}
        messages.add_message(
            request,
            messages.INFO,
            'Domain successfully deleted!')
    else:
        responseData = {'status': 'false'}
        messages.add_message(
            request,
            messages.ERROR,
            'Oops! Domain could not be deleted!')
    return http.JsonResponse(responseData)


@has_permission_decorator(PERM_MODIFY_TARGETS, redirect_url=FOUR_OH_FOUR_URL)
def delete_targets(request, slug):
    if request.method == "POST":
        list_of_domains = []
        for key, value in request.POST.items():
            if key != "list_target_table_length" and key != "csrfmiddlewaretoken":
                list_of_domains.append(value)
                Domain.objects.filter(id=value).delete()
        messages.add_message(
            request,
            messages.INFO,
            f'{len(list_of_domains)} targets deleted!')
    return http.HttpResponseRedirect(reverse('list_target', kwargs={'slug': slug}))


@has_permission_decorator(PERM_MODIFY_TARGETS, redirect_url=FOUR_OH_FOUR_URL)
def update_target(request, slug, id):
    domain = get_object_or_404(Domain, id=id)
    form = UpdateTargetForm()
    if request.method == "POST":
        form = UpdateTargetForm(request.POST, instance=domain)
        if form.is_valid():
            form.save()
            messages.add_message(
                request,
                messages.INFO,
                f'Domain {domain.name} modified!')
            return http.HttpResponseRedirect(reverse('list_target', kwargs={'slug': slug}))
    else:
        form.set_value(domain.name, domain.description, domain.h1_team_handle)
    context = {
        'list_target_li': 'active',
        'target_data_active': 'active',
        "domain": domain,
        "form": form
    }
    return render(request, 'target/update.html', context)

def target_summary(request, slug, id):
    """Summary of a target (domain). Contains aggregated information on all
    objects (Subdomain, EndPoint, Vulnerability, Emails, ...) found across all
    scans.

    Args:
        request: Django request.
        id: Domain id.
    """
    context = {}

    # Domain
    target = get_object_or_404(Domain, id=id)
    context['target'] = target

    # Scan History
    scan = ScanHistory.objects.filter(domain__id=id)
    context['recent_scans'] = scan.order_by('-start_scan_date')[:4]
    context['scan_count'] = scan.count()
    last_week = timezone.now() - timedelta(days=7)
    context['this_week_scan_count'] = (
        scan
        .filter(start_scan_date__gte=last_week)
        .count()
    )

    # Scan Engines
    context['scan_engines'] = EngineType.objects.order_by('engine_name').all()

    # Subdomains
    subdomains = (
        Subdomain.objects
        .filter(target_domain__id=id)
        .values('name')
        .distinct()
    )
    context['subdomain_count'] = subdomains.count()
    context['alive_count'] = subdomains.filter(http_status__exact=200).count()

    # Endpoints
    endpoints = (
        EndPoint.objects
        .filter(target_domain__id=id)
        .values('http_url')
        .distinct()
    )
    context['endpoint_count'] = endpoints.count()
    context['endpoint_alive_count'] = endpoints.filter(http_status__exact=200).count()

    # Vulnerabilities
    vulnerabilities = Vulnerability.objects.filter(target_domain__id=id)
    unknown_count = vulnerabilities.filter(severity=-1).count()
    info_count = vulnerabilities.filter(severity=0).count()
    low_count = vulnerabilities.filter(severity=1).count()
    medium_count = vulnerabilities.filter(severity=2).count()
    high_count = vulnerabilities.filter(severity=3).count()
    critical_count = vulnerabilities.filter(severity=4).count()
    ignore_info_count = sum([low_count, medium_count, high_count, critical_count])
    context['unknown_count'] = unknown_count
    context['info_count'] = info_count
    context['low_count'] = low_count
    context['medium_count'] = medium_count
    context['high_count'] = high_count
    context['critical_count'] = critical_count
    context['total_vul_ignore_info_count'] = ignore_info_count
    context['most_common_vulnerability'] = (
        vulnerabilities
        .exclude(severity=0)
        .values("name", "severity")
        .annotate(count=Count('name'))
        .order_by("-count")[:10]
    )
    context['vulnerability_count'] = vulnerabilities.count()
    context['vulnerability_list'] = (
        vulnerabilities
        .order_by('-severity')
        .all()[:30]
    )

    # Vulnerability Tags
    context['most_common_tags'] = (
        VulnerabilityTags.objects
        .filter(vuln_tags__in=vulnerabilities)
        .annotate(nused=Count('vuln_tags'))
        .order_by('-nused')
        .values('name', 'nused')[:7]
    )

    # Emails
    emails = (
        Email.objects
        .filter(emails__in=scan)
        .distinct()
    )
    context['exposed_count'] = emails.exclude(password__isnull=True).count()
    context['email_count'] = emails.count()

    # Employees
    context['employees_count'] = (
        Employee.objects
        .filter(employees__in=scan)
        .count()
    )

    # HTTP Statuses
    context['http_status_breakdown'] = (
        subdomains
        .exclude(http_status=0)
        .values('http_status')
        .annotate(Count('http_status'))
    )

    # CVEs
    context['most_common_cve'] = (
        CveId.objects
        .filter(cve_ids__in=vulnerabilities)
        .annotate(nused=Count('cve_ids'))
        .order_by('-nused')
        .values('name', 'nused')[:7]
    )

    # CWEs
    context['most_common_cwe'] = (
        CweId.objects
        .filter(cwe_ids__in=vulnerabilities)
        .annotate(nused=Count('cwe_ids'))
        .order_by('-nused')
        .values('name', 'nused')[:7]
    )

    # Country ISOs
    subdomains = Subdomain.objects.filter(target_domain__id=id)
    ip_addresses = IpAddress.objects.filter(ip_addresses__in=subdomains)
    context['asset_countries'] = (
        CountryISO.objects
        .filter(ipaddress__in=ip_addresses)
        .annotate(count=Count('iso'))
        .order_by('-count')
    )

    context['slug'] = slug

    return render(request, 'target/summary.html', context)


@has_permission_decorator(PERM_MODIFY_TARGETS, redirect_url=FOUR_OH_FOUR_URL)
def add_organization(request, slug):
    form = AddOrganizationForm(request.POST or None, project=slug)
    if request.method == "POST":
        if form.is_valid():
            data = form.cleaned_data
            project = Project.objects.get(slug=slug)
            organization = Organization.objects.create(
                name=data['name'],
                description=data['description'],
                project=project,
                insert_date=timezone.now())
            for domain_id in request.POST.getlist("domains"):
                domain = Domain.objects.get(id=domain_id)
                organization.domains.add(domain)
            messages.add_message(
                request,
                messages.INFO,
                f'Organization {data["name"]} added successfully')
            return http.HttpResponseRedirect(reverse('list_organization', kwargs={'slug': slug}))
    context = {
        "organization_active": "active",
        "form": form
    }
    return render(request, 'organization/add.html', context)

def list_organization(request, slug):
    organizations = Organization.objects.filter(project__slug=slug).order_by('-insert_date')
    context = {
        'organization_active': 'active',
        'organizations': organizations
    }
    return render(request, 'organization/list.html', context)


@has_permission_decorator(PERM_MODIFY_TARGETS, redirect_url=FOUR_OH_FOUR_URL)
def delete_organization(request, id):
    if request.method == "POST":
        obj = get_object_or_404(Organization, id=id)
        obj.delete()
        responseData = {'status': 'true'}
        messages.add_message(
            request,
            messages.INFO,
            'Organization successfully deleted!')
    else:
        responseData = {'status': 'false'}
        messages.add_message(
            request,
            messages.ERROR,
            'Oops! Organization could not be deleted!')
    return http.JsonResponse(responseData)


@has_permission_decorator(PERM_MODIFY_TARGETS, redirect_url=FOUR_OH_FOUR_URL)
def update_organization(request, slug, id):
    organization = get_object_or_404(Organization, id=id)
    form = UpdateOrganizationForm()
    if request.method == "POST":
        print(request.POST.getlist("domains"))
        form = UpdateOrganizationForm(request.POST, instance=organization)
        if form.is_valid():
            data = form.cleaned_data
            for domain in organization.get_domains():
                organization.domains.remove(domain)

            organization_obj = Organization.objects.filter(id=id)
            organization_obj.update(
                name=data['name'],
                description=data['description'],
            )
            for domain_id in request.POST.getlist("domains"):
                domain = Domain.objects.get(id=domain_id)
                organization.domains.add(domain)
            msg = f'Organization {organization.name} modified!'
            logger.info(msg)
            messages.add_message(
                request,
                messages.INFO,
                msg)
            return http.HttpResponseRedirect(reverse('list_organization', kwargs={'slug': slug}))
    else:
        domain_list = organization.get_domains().values_list('id', flat=True)
        domain_list = [str(id) for id in domain_list]
        form.set_value(organization.name, organization.description)
    context = {
        'list_organization_li': 'active',
        'organization_data_active': 'true',
        "organization": organization,
        "domain_list": mark_safe(domain_list),
        "form": form
    }
    return render(request, 'organization/update.html', context)


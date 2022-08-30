import csv
import io
import logging
import os
from datetime import timedelta
from functools import reduce
from operator import and_, or_

import validators
from django import http
from django.conf import settings
from django.contrib import messages
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.utils.safestring import mark_safe
from reNgine.common_func import *
from reNgine.tasks import query_whois
from scanEngine.models import *
from startScan.models import *
from targetApp.forms import *
from targetApp.models import *

logger = logging.getLogger()


def index(request):
    # TODO bring default target page
    return render(request, 'target/index.html')


def add_target(request):
    form = AddTargetForm(request.POST or None)

    if request.method == "POST":
        added_target_count = 0
        if not form.is_valid():
            for error in form.errors:
                messages.add_message(request, messages.ERROR, error)
            return http.HttpResponseRedirect(reverse('add_target'))
        data = form.cleaned_data
        single_target = request.POST.get('add-single-target')
        multiple_targets = request.POST.get('add-multiple-targets')
        ip_target =  request.POST.get('add-ip-target')
        do_fetch_whois = request.POST.get('fetch_whois_checkbox', '') == 'on'
        try:
            # Single target
            if single_target:
                name = data['name']
                logger.info(f'Adding single target {name} ...')
                domain, _ = Domain.objects.get_or_create(name=name)
                for k, v in data.items():
                    setattr(domain, k, v)
                if not domain.insert_date:
                    domain.insert_date = timezone.now()
                    domain.save()
                logger.info(f'Domain {domain.name} added/updated in DB')
                messages.add_message(
                    request,
                    messages.INFO,
                    f'Target domain {domain.name} added successfully')

                if do_fetch_whois:
                    query_whois.apply_async(args=(domain.name,))

                return http.HttpResponseRedirect(reverse('list_target'))

            # Multiple targets
            elif multiple_targets:
                bulk_targets = [t.rstrip() for t in request.POST['addTargets'].split('\n')]
                bulk_targets = [t for t in bulk_targets if t]
                description = request.POST.get('targetDescription', '')
                h1_team_handle = request.POST.get('targetH1TeamHandle')
                for target in bulk_targets:
                    domain_query = Domain.objects.filter(name=target)
                    if not domain_query.exists() and validators.domain(target):
                        Domain.objects.create(
                            name=target.rstrip("\n"),
                            description=description,
                            h1_team_handle=h1_team_handle,
                            insert_date=timezone.now())
                        added_target_count += 1

            # IP to domain conversion
            elif ip_target:
                domains = request.POST.getlist('resolved_ip_domains')
                description = request.POST.get('targetDescription', '')
                ip_address_cidr = request.POST.get('ip_address', '')
                h1_team_handle = request.POST.get('targetH1TeamHandle')
                for domain in domains:
                    domain_query = Domain.objects.filter(name=domain)
                    if not domain_query.exists():
                        if not validators.domain(domain):
                            messages.add_message(
                                request,
                                messages.ERROR,
                                f'Domain {domain} is not a valid domain name. Skipping.')
                            continue
                        Domain.objects.create(
                            name=domain,
                            description=description,
                            h1_team_handle=h1_team_handle,
                            ip_address_cidr=ip_address_cidr,
                            insert_date=timezone.now())
                        added_target_count += 1

            # Import from txt / csv
            elif 'import-txt-target' in request.POST or 'import-csv-target' in request.POST:
                txt_file = request.FILES.get('txtFile')
                csv_file = request.FILES.get('csvFile')
                if not (txt_file or csv_file):
                    messages.add_message(
                        request, 
                        messages.ERROR, 
                        'Files uploaded are not .txt or .csv files.')
                    return http.HttpResponseRedirect(reverse('add_target'))

                if txt_file:
                    is_txt = txt_file.content_type == 'text/plain' or txt_file.name.split('.')[-1] == 'txt'
                    if not is_txt:
                        messages.add_message(
                            request,
                            messages.ERROR,
                            'File is not a valid TXT file')
                        return http.HttpResponseRedirect(reverse('add_target'))
                    txt_content = txt_file.read().decode('UTF-8')
                    io_string = io.StringIO(txt_content)
                    for target in io_string:
                        target_domain = target.rstrip("\n").rstrip("\r")
                        domain_query = Domain.objects.filter(name=target_domain)
                        if not domain_query.exists():
                            if not validators.domain(domain):
                                messages.add_message(request, messages.ERROR, f'Domain {domain} is not a valid domain name. Skipping.')
                                continue
                            Domain.objects.create(
                                name=target_domain,
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
                        return http.HttpResponseRedirect(reverse('add_target'))
                    csv_content = csv_file.read().decode('UTF-8')
                    io_string = io.StringIO(csv_content)
                    for column in csv.reader(io_string, delimiter=','):
                        domain = column[0]
                        description = None if len(column) == 1 else column[1]
                        domain_query = Domain.objects.filter(name=domain)
                        if not domain_query.exists():
                            if not validators.domain(domain):
                                messages.add_message(request, messages.ERROR, f'Domain {domain} is not a valid domain name. Skipping.')
                                continue
                            Domain.objects.create(
                                name=domain,
                                description=description,
                                insert_date=timezone.now())
                            added_target_count += 1

        except Exception as e:
            logger.exception(e)
            messages.add_message(
                request,
                messages.ERROR,
                f'Exception while adding domain: {e}'
            )
            return http.HttpResponseRedirect(reverse('add_target'))

        # No targets added, redirect to add target page
        if added_target_count == 0:
            messages.add_message(
                request,
                messages.ERROR,
                'Oops! Could not import any targets, either targets already exists or is not a valid target.')
            return http.HttpResponseRedirect(reverse('add_target'))

        # Targets added successfully, redirect to targets list
        messages.add_message(request, messages.SUCCESS, f'{added_target_count} targets added successfully')
        return http.HttpResponseRedirect(reverse('list_target'))

    # GET request
    context = {
        "add_target_li": "active",
        "target_data_active": "active",
        'form': form
    }
    return render(request, 'target/add.html', context)

def list_target(request):
    context = {
        'list_target_li': 'active',
        'target_data_active': 'active'
    }
    return render(request, 'target/list.html', context)


def delete_target(request, id):
    obj = get_object_or_404(Domain, id=id)
    if request.method == "POST":
        os.system(
            'rm -rf ' +
            settings.TOOL_LOCATION +
            'scan_results/' +
            obj.name + '*')
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


def delete_targets(request):
    if request.method == "POST":
        list_of_domains = []
        for key, value in request.POST.items():
            if key != "list_target_table_length" and key != "csrfmiddlewaretoken":
                Domain.objects.filter(id=value).delete()
        messages.add_message(
            request,
            messages.INFO,
            'Targets deleted!')
    return http.HttpResponseRedirect(reverse('list_target'))


def update_target(request, id):
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
            return http.HttpResponseRedirect(reverse('list_target'))
    else:
        form.set_value(domain.name, domain.description, domain.h1_team_handle)
    context = {
        'list_target_li': 'active',
        'target_data_active': 'active',
        "domain": domain,
        "form": form
    }
    return render(request, 'target/update.html', context)

def target_summary(request, id):
    context = {}
    target = get_object_or_404(Domain, id=id)
    context['target'] = target
    context['scan_count'] = ScanHistory.objects.filter(
        domain_id=id).count()
    last_week = timezone.now() - timedelta(days=7)
    context['this_week_scan_count'] = ScanHistory.objects.filter(
        domain_id=id, start_scan_date__gte=last_week).count()
    subdomains = Subdomain.objects.filter(
        target_domain__id=id).values('name').distinct()
    endpoints = EndPoint.objects.filter(
        target_domain__id=id).values('http_url').distinct()

    vulnerabilities = Vulnerability.objects.filter(target_domain__id=id)
    vulnerability_count = vulnerabilities.count()
    context['subdomain_count'] = subdomains.count()
    context['alive_count'] = subdomains.filter(http_status__exact=200).count()
    context['endpoint_count'] = endpoints.count()
    context['endpoint_alive_count'] = endpoints.filter(http_status__exact=200).count()

    context['scan_engines'] = EngineType.objects.all()

    unknown_count = vulnerabilities.filter(severity=-1).count()
    info_count = vulnerabilities.filter(severity=0).count()
    low_count = vulnerabilities.filter(severity=1).count()
    medium_count = vulnerabilities.filter(severity=2).count()
    high_count = vulnerabilities.filter(severity=3).count()
    critical_count = vulnerabilities.filter(severity=4).count()

    context['unknown_count'] = unknown_count
    context['info_count'] = info_count
    context['low_count'] = low_count
    context['medium_count'] = medium_count
    context['high_count'] = high_count
    context['critical_count'] = critical_count

    context['total_vul_ignore_info_count'] = low_count + \
        medium_count + high_count + critical_count

    context['most_common_vulnerability'] = Vulnerability.objects.exclude(severity=0).filter(target_domain__id=id).values("name", "severity").annotate(count=Count('name')).order_by("-count")[:10]

    emails = Email.objects.filter(emails__in=ScanHistory.objects.filter(domain__id=id).distinct())

    context['exposed_count'] = emails.exclude(password__isnull=True).count()

    context['email_count'] = emails.count()

    context['employees_count'] = Employee.objects.filter(
        employees__in=ScanHistory.objects.filter(id=id)).count()

    context['recent_scans'] = ScanHistory.objects.filter(
        domain=id).order_by('-start_scan_date')[:4]

    context['vulnerability_count'] = vulnerability_count

    context['vulnerability_list'] = Vulnerability.objects.filter(
        target_domain__id=id).order_by('-severity').all()[:30]

    context['http_status_breakdown'] = Subdomain.objects.filter(target_domain=id).exclude(http_status=0).values('http_status').annotate(Count('http_status'))

    context['most_common_cve'] = CveId.objects.filter(cve_ids__in=Vulnerability.objects.filter(target_domain__id=id)).annotate(nused=Count('cve_ids')).order_by('-nused').values('name', 'nused')[:7]
    context['most_common_cwe'] = CweId.objects.filter(cwe_ids__in=Vulnerability.objects.filter(target_domain__id=id)).annotate(nused=Count('cwe_ids')).order_by('-nused').values('name', 'nused')[:7]
    context['most_common_tags'] = VulnerabilityTags.objects.filter(vuln_tags__in=Vulnerability.objects.filter(target_domain__id=id)).annotate(nused=Count('vuln_tags')).order_by('-nused').values('name', 'nused')[:7]

    context['asset_countries'] = CountryISO.objects.filter(ipaddress__in=IpAddress.objects.filter(ip_addresses__in=Subdomain.objects.filter(target_domain__id=id))).annotate(count=Count('iso')).order_by('-count')
    return render(request, 'target/summary.html', context)

def add_organization(request):
    form = AddOrganizationForm(request.POST or None)
    data = form.cleaned_data
    if request.method == "POST":
        if form.is_valid():
            organization = Organization.objects.create(
                name=data['name'],
                description=data['description'],
                insert_date=timezone.now())
            for domain_id in request.POST.getlist("domains"):
                domain = Domain.objects.get(id=domain_id)
                organization.domains.add(domain)
            messages.add_message(
                request,
                messages.INFO,
                f'Organization {data["name"]} added successfully')
            return http.HttpResponseRedirect(reverse('list_organization'))
    context = {
        "organization_active": "active",
        "form": form
    }
    return render(request, 'organization/add.html', context)

def list_organization(request):
    organizations = Organization.objects.all().order_by('-insert_date')
    context = {
        'organization_active': 'active',
        'organizations': organizations
    }
    return render(request, 'organization/list.html', context)

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

def update_organization(request, id):
    organization = get_object_or_404(Organization, id=id)
    form = UpdateOrganizationForm()
    data = form.cleaned_data
    if request.method == "POST":
        print(request.POST.getlist("domains"))
        form = UpdateOrganizationForm(request.POST, instance=organization)
        if form.is_valid():
            organization_obj = Organization.objects.filter(
                id=id
            )

            for domain in organization.get_domains():
                organization.domains.remove(domain)

            organization_obj.update(
                name=data['name'],
                description=data['description'],
            )
            for domain_id in request.POST.getlist("domains"):
                domain = Domain.objects.get(id=domain_id)
                organization.domains.add(domain)
            messages.add_message(
                request,
                messages.INFO,
                f'Organization {organization.name} modified!')
            return http.HttpResponseRedirect(reverse('list_organization'))
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

import validators
import csv
import io
import os

from datetime import timedelta
from operator import and_, or_
from functools import reduce
from django import http
from django.shortcuts import render, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.urls import reverse
from django.conf import settings
from django.db.models import Count, Q
from django.utils.safestring import mark_safe

from targetApp.models import *
from startScan.models import *
from scanEngine.models import *
from targetApp.forms import *
from reNgine.common_func import *



def index(request):
    # TODO bring default target page
    return render(request, 'target/index.html')


def add_target(request):
    form = AddTargetForm(request.POST or None)
    if request.method == "POST":
        if form.is_valid():
            Domain.objects.create(
                **form.cleaned_data,
                insert_date=timezone.now())
            messages.add_message(
                request,
                messages.INFO,
                'Target domain ' +
                form.cleaned_data['name'] +
                ' added successfully')
            return http.HttpResponseRedirect(reverse('list_target'))
    context = {
        "add_target_li": "active",
        "target_data_active": "active",
        'form': form}
    return render(request, 'target/add.html', context)


def add_bulk_targets(request):
    context = {
        "add_targets_li": "active",
        "target_data_active": "active", }
    if request.method == "POST":
        bulk_targets = [target.rstrip()
                        for target in request.POST['addTargets'].split('\n')]
        bulk_targets = [target for target in bulk_targets if target]
        description = request.POST['targetDescription'] if 'targetDescription' in request.POST else ''
        target_count = 0
        for target in bulk_targets:
            if not Domain.objects.filter(
                    name=target).exists() and validators.domain(target):
                Domain.objects.create(
                    name=target.rstrip("\n"),
                    description=description,
                    insert_date=timezone.now())
                target_count += 1
        if target_count:
            messages.add_message(request, messages.SUCCESS, str(
                target_count) + ' targets added successfully!')
            return http.HttpResponseRedirect(reverse('list_target'))
        else:
            messages.add_message(
                request,
                messages.ERROR,
                'Oops! Could not import any targets, either targets already exists or is not a valid target.')
    return render(request, 'target/bulk_add_targets.html', context)


def import_targets(request):
    context = {}
    context['import_target_li'] = 'active'
    context['target_data_active'] = 'active'
    if request.method == 'POST':
        if 'txtFile' in request.FILES:
            txt_file = request.FILES['txtFile']
            if txt_file.content_type == 'text/plain':
                target_count = 0
                txt_content = txt_file.read().decode('UTF-8')
                io_string = io.StringIO(txt_content)
                for target in io_string:
                    if not Domain.objects.filter(
                            name=target.rstrip("\n")).exists() and validators.domain(target):
                        Domain.objects.create(
                            name=target.rstrip("\n"),
                            insert_date=timezone.now())
                        target_count += 1
                if target_count:
                    messages.add_message(request, messages.SUCCESS, str(
                        target_count) + ' targets added successfully!')
                    return http.HttpResponseRedirect(reverse('list_target'))
                else:
                    messages.add_message(
                        request,
                        messages.ERROR,
                        'Oops! File format was invalid, could not import any targets.')
            else:
                messages.add_message(
                    request, messages.ERROR, 'Invalid File type!')
        elif 'csvFile' in request.FILES:
            csv_file = request.FILES['csvFile']
            if csv_file.content_type == 'text/csv':
                target_count = 0
                csv_content = csv_file.read().decode('UTF-8')
                io_string = io.StringIO(csv_content)
                for column in csv.reader(io_string, delimiter=','):
                    if not Domain.objects.filter(
                            name=column[0]).exists() and validators.domain(
                            column[0]):
                        Domain.objects.create(
                            name=column[0],
                            description=column[1],
                            insert_date=timezone.now())
                        target_count += 1
                if target_count:
                    messages.add_message(request, messages.SUCCESS, str(
                        target_count) + ' targets added successfully!')
                    return http.HttpResponseRedirect(reverse('list_target'))
                else:
                    messages.add_message(
                        request,
                        messages.ERROR,
                        'Oops! File format was invalid, could not import any targets.')
            else:
                messages.add_message(
                    request, messages.ERROR, 'Invalid File type!')
    return render(request, 'target/import.html', context)


def list_target(request):
    domains = Domain.objects.all().order_by('-insert_date')
    context = {
        'list_target_li': 'active',
        'target_data_active': 'active',
        'domains': domains}
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
    context = {}
    if request.method == "POST":
        list_of_domains = []
        for key, value in request.POST.items():
            if key != "style-2_length" and key != "csrfmiddlewaretoken":
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
                'Domain {} modified!'.format(domain.name))
            return http.HttpResponseRedirect(reverse('list_target'))
    else:
        form.set_value(domain.name, domain.description)
    context = {
        'list_target_li': 'active',
        'target_data_active': 'active',
        "domain": domain,
        "form": form}
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
    subdomain_count = Subdomain.objects.filter(
        target_domain__id=id).values('name').distinct().count()
    endpoint_count = EndPoint.objects.filter(
        target_domain__id=id).values('http_url').distinct().count()
    vulnerability_count = Vulnerability.objects.filter(
        target_domain__id=id).count()
    context['subdomain_count'] = subdomain_count
    context['endpoint_count'] = endpoint_count
    context['vulnerability_count'] = vulnerability_count
    if ScanHistory.objects.filter(
        domain=id).filter(
        scan_type__subdomain_discovery=True).filter(
            scan_status=2).count() > 1:
        last_scan = ScanHistory.objects.filter(
            domain=id).filter(
            scan_type__subdomain_discovery=True).filter(
            scan_status=2).order_by('-start_scan_date')

        scanned_host_q1 = Subdomain.objects.filter(
            target_domain__id=id).exclude(
            scan_history__id=last_scan[0].id).values('name')
        scanned_host_q2 = Subdomain.objects.filter(
            scan_history__id=last_scan[0].id).values('name')

        context['new_subdomains'] = scanned_host_q2.difference(scanned_host_q1)
        context['removed_subdomains'] = scanned_host_q1.difference(
            scanned_host_q2)

    if ScanHistory.objects.filter(
            domain=id).filter(
            scan_type__fetch_url=True).filter(scan_status=2).count() > 1:

        last_scan = ScanHistory.objects.filter(
            domain=id).filter(
            scan_type__fetch_url=True).filter(
            scan_status=2).order_by('-start_scan_date')

        endpoint_q1 = EndPoint.objects.filter(
            target_domain__id=id).exclude(
            scan_history__id=last_scan[0].id).values('http_url')
        endpoint_q2 = EndPoint.objects.filter(
            scan_history__id=last_scan[0].id).values('http_url')

        context['new_urls'] = endpoint_q2.difference(endpoint_q1)
        context['removed_urls'] = endpoint_q1.difference(endpoint_q2)

    context['recent_scans'] = ScanHistory.objects.filter(
        domain=id).order_by('-start_scan_date')[:3]
    context['info_count'] = Vulnerability.objects.filter(
        target_domain=id).filter(severity=0).count()
    context['low_count'] = Vulnerability.objects.filter(
        target_domain=id).filter(severity=1).count()
    context['medium_count'] = Vulnerability.objects.filter(
        target_domain=id).filter(severity=2).count()
    context['high_count'] = Vulnerability.objects.filter(
        target_domain=id).filter(severity=3).count()
    context['critical_count'] = Vulnerability.objects.filter(
        target_domain=id).filter(severity=4).count()
    context['most_common_vulnerability'] = Vulnerability.objects.filter(target_domain=id).values(
        "name", "severity").exclude(severity=0).annotate(count=Count('name')).order_by("-count")[:7]
    context['interesting_subdomain'] = get_interesting_subdomains(target=id)
    context['interesting_endpoint'] = get_interesting_endpoint(target=id)
    context['scan_history'] = ScanHistory.objects.filter(
        domain=id).order_by('-start_scan_date')
    return render(request, 'target/summary.html', context)

def add_organization(request):
    form = AddOrganizationForm(request.POST or None)
    if request.method == "POST":
        print(form.errors)
        if form.is_valid():
            organization = Organization.objects.create(
                name=form.cleaned_data['name'],
                description=form.cleaned_data['description'],
                insert_date=timezone.now())
            for domain_id in request.POST.getlist("domains"):
                domain = Domain.objects.get(id=domain_id)
                organization.domains.add(domain)
            messages.add_message(
                request,
                messages.INFO,
                'Organization ' +
                form.cleaned_data['name'] +
                ' added successfully')
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
                name=form.cleaned_data['name'],
                description=form.cleaned_data['description'],
            )
            for domain_id in request.POST.getlist("domains"):
                domain = Domain.objects.get(id=domain_id)
                organization.domains.add(domain)
            messages.add_message(
                request,
                messages.INFO,
                'Organization {} modified!'.format(organization.name))
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

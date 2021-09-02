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
    add_target_form = AddTargetForm(request.POST or None)
    if request.method == "POST":
        if 'add-target' in request.POST and add_target_form.is_valid():
            Domain.objects.create(
                **add_target_form.cleaned_data,
                insert_date=timezone.now())
            messages.add_message(
                request,
                messages.INFO,
                'Target domain ' +
                add_target_form.cleaned_data['name'] +
                ' added successfully')
            return http.HttpResponseRedirect(reverse('list_target'))
        elif 'add-multiple-targets' in request.POST:
            bulk_targets = [target.rstrip()
                            for target in request.POST['addTargets'].split('\n')]
            bulk_targets = [target for target in bulk_targets if target]
            description = request.POST['targetDescription'] if 'targetDescription' in request.POST else ''
            h1_team_handle = request.POST['targetH1TeamHandle'] if 'targetH1TeamHandle' in request.POST else None
            target_count = 0
            for target in bulk_targets:
                if not Domain.objects.filter(
                        name=target).exists() and validators.domain(target):
                    Domain.objects.create(
                        name=target.rstrip("\n"),
                        description=description,
                        h1_team_handle=h1_team_handle,
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
                return http.HttpResponseRedirect(reverse('add_target'))
        elif 'import-txt-target' in request.POST or 'import-csv-target' in request.POST:
            if 'txtFile' in request.FILES:
                txt_file = request.FILES['txtFile']
                if txt_file.content_type == 'text/plain':
                    target_count = 0
                    txt_content = txt_file.read().decode('UTF-8')
                    io_string = io.StringIO(txt_content)
                    for target in io_string:
                        target_domain = target.rstrip("\n").rstrip("\r")
                        if not Domain.objects.filter(
                                name=target_domain).exists() and validators.domain(target_domain):
                            Domain.objects.create(
                                name=target_domain,
                                insert_date=timezone.now())
                            target_count += 1
                    if target_count:
                        messages.add_message(request, messages.SUCCESS, str(
                            target_count) + ' targets added successfully!')
                    else:
                        messages.add_message(
                            request,
                            messages.ERROR,
                            'Error importing targets, either targets already exist or CSV file is not valid.')
                        return http.HttpResponseRedirect(reverse('add_target'))
                else:
                    messages.add_message(
                        request, messages.ERROR, 'Invalid File type!')
                    return http.HttpResponseRedirect(reverse('add_target'))
            elif 'csvFile' in request.FILES:
                csv_file = request.FILES['csvFile']
                if csv_file.content_type == 'text/csv' or csv_file.name.split('.')[1]:
                    target_count = 0
                    csv_content = csv_file.read().decode('UTF-8')
                    io_string = io.StringIO(csv_content)
                    for column in csv.reader(io_string, delimiter=','):
                        target_domain = column[0]
                        description = None if len(column) == 1 else column[1]
                        if not Domain.objects.filter(
                                name=target_domain).exists() and validators.domain(
                                target_domain):
                            Domain.objects.create(
                                name=target_domain,
                                description=description,
                                insert_date=timezone.now())
                            target_count += 1
                    if target_count:
                        messages.add_message(request, messages.SUCCESS, str(
                            target_count) + ' targets added successfully!')
                    else:
                        messages.add_message(
                            request,
                            messages.ERROR,
                            'Error importing targets, either targets already exist or CSV file is not valid.')
                        return http.HttpResponseRedirect(reverse('add_target'))
                else:
                    messages.add_message(
                        request, messages.ERROR, 'Invalid File type!')
                    return http.HttpResponseRedirect(reverse('add_target'))
            return http.HttpResponseRedirect(reverse('list_target'))
    context = {
        "add_target_li": "active",
        "target_data_active": "active",
        'form': add_target_form}
    return render(request, 'target/add.html', context)

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
                'Domain {} modified!'.format(domain.name))
            return http.HttpResponseRedirect(reverse('list_target'))
    else:
        form.set_value(domain.name, domain.description, domain.h1_team_handle)
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
    subdomains = Subdomain.objects.filter(
        target_domain__id=id).values('name').distinct()
    endpoints = EndPoint.objects.filter(
        target_domain__id=id).values('http_url').distinct()
    vulnerability_count = Vulnerability.objects.filter(
        target_domain__id=id).count()
    context['subdomain_count'] = subdomains.count()
    context['alive_count'] = subdomains.filter(http_status__exact=200).count()
    context['endpoint_count'] = endpoints.count()
    context['endpoint_alive_count'] = endpoints.filter(http_status__exact=200).count()

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

    emails = Email.objects.filter(emails__in=ScanHistory.objects.filter(domain__id=id).distinct())

    context['exposed_count'] = emails.exclude(password__isnull=True).count()

    context['email_count'] = emails.count()

    context['employees_count'] = Employee.objects.filter(
        employees__in=ScanHistory.objects.filter(id=id)).count()

    context['recent_scans'] = ScanHistory.objects.filter(
        domain=id).order_by('-start_scan_date')[:4]

    context['vulnerability_count'] = vulnerability_count

    context['vulnerability_list'] = Vulnerability.objects.filter(
        target_domain__id=id).order_by('-severity').all()[:20]

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

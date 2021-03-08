import validators
import csv
import io
import os

from datetime import timedelta
from operator import and_, or_
from functools import reduce
from django import http
from django.shortcuts import render, get_object_or_404
from .models import Domain
from startScan.models import ScanHistory, WayBackEndPoint, ScannedHost, VulnerabilityScan, ScanActivity
from scanEngine.models import InterestingLookupModel
from django.contrib import messages
from targetApp.forms import AddTargetForm, UpdateTargetForm
from django.utils import timezone
from django.urls import reverse
from django.conf import settings
from django.db.models import Count, Q

from reNgine.common_func import *


def index(request):
    # TODO bring default target page
    return render(request, 'target/index.html')


def add_target_form(request):
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
                form.cleaned_data['domain_name'] +
                ' added successfully')
            return http.HttpResponseRedirect(reverse('list_target'))
    context = {
        "add_target_li": "active",
        "target_data_active": "true",
        'form': form}
    return render(request, 'target/add.html', context)


def import_targets(request):
    context = {}
    context['import_target_li'] = 'active'
    context['target_data_active'] = 'true'
    if request.method == 'POST':
        if 'txtFile' in request.FILES:
            txt_file = request.FILES['txtFile']
            if txt_file.content_type == 'text/plain':
                target_count = 0
                txt_content = txt_file.read().decode('UTF-8')
                io_string = io.StringIO(txt_content)
                for target in io_string:
                    if validators.domain(target):
                        Domain.objects.create(
                            domain_name=target.rstrip("\n"),
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
                    if validators.domain(column[0]):
                        Domain.objects.create(
                            domain_name=column[0],
                            domain_description=column[1],
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
        'target_data_active': 'true',
        'domains': domains}
    return render(request, 'target/list.html', context)


def delete_target(request, id):
    obj = get_object_or_404(Domain, id=id)
    if request.method == "POST":
        os.system(
            'rm -rf ' +
            settings.TOOL_LOCATION +
            'scan_results/' +
            obj.domain_name + '*')
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
            messages.INFO,
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


def update_target_form(request, id):
    domain = get_object_or_404(Domain, id=id)
    form = UpdateTargetForm()
    if request.method == "POST":
        form = UpdateTargetForm(request.POST, instance=domain)
        if form.is_valid():
            form.save()
            messages.add_message(
                request,
                messages.INFO,
                'Domain edited successfully')
            return http.HttpResponseRedirect(reverse('list_target'))
    else:
        form.set_value(domain.domain_name, domain.domain_description)
    context = {
        'list_target_li': 'active',
        'target_data_active': 'true',
        "domain": domain,
        "form": form}
    return render(request, 'target/update.html', context)


def target_summary(request, id):
    context = {}
    target = get_object_or_404(Domain, id=id)
    context['target'] = target
    context['scan_count'] = ScanHistory.objects.filter(
        domain_name_id=id).count()
    last_week = timezone.now() - timedelta(days=7)
    context['this_week_scan_count'] = ScanHistory.objects.filter(
        domain_name_id=id, last_scan_date__gte=last_week).count()
    subdomain_count = ScannedHost.objects.filter(
        target_domain__id=id).values('subdomain').distinct().count()
    endpoint_count = WayBackEndPoint.objects.filter(
        target_domain__id=id).values('http_url').distinct().count()
    vulnerability_count = VulnerabilityScan.objects.filter(
        target_domain__id=id).count()
    context['subdomain_count'] = subdomain_count
    context['endpoint_count'] = endpoint_count
    context['vulnerability_count'] = vulnerability_count
    if ScanHistory.objects.filter(domain_name=id).count() > 1:
        subdomain_count_query = ScanHistory.objects.filter(
            domain_name=id).order_by('-last_scan_date')[0:2]
        context['subdomain_difference'] = ScannedHost.objects.filter(
            scan_history__id=subdomain_count_query[0].id).count() - ScannedHost.objects.filter(
            scan_history__id=subdomain_count_query[1].id).count()

        context['endpoint_difference'] = WayBackEndPoint.objects.filter(
            url_of__id=subdomain_count_query[0].id).count() - WayBackEndPoint.objects.filter(
            url_of__id=subdomain_count_query[1].id).count()

        context['vulnerability_difference'] = VulnerabilityScan.objects.filter(
            vulnerability_of__id=subdomain_count_query[0].id).count() - VulnerabilityScan.objects.filter(
            vulnerability_of__id=subdomain_count_query[1].id).count()
    else:
        context['subdomain_difference'] = subdomain_count
        context['endpoint_difference'] = endpoint_count
        context['vulnerability_difference'] = vulnerability_count
    context['recent_scans'] = ScanHistory.objects.filter(
        domain_name=id).order_by('-last_scan_date')[:3]
    context['info_count'] = VulnerabilityScan.objects.filter(
        target_domain=id).filter(severity=0).count()
    context['low_count'] = VulnerabilityScan.objects.filter(
        target_domain=id).filter(severity=1).count()
    context['medium_count'] = VulnerabilityScan.objects.filter(
        target_domain=id).filter(severity=2).count()
    context['high_count'] = VulnerabilityScan.objects.filter(
        target_domain=id).filter(severity=3).count()
    context['critical_count'] = VulnerabilityScan.objects.filter(
        target_domain=id).filter(severity=4).count()
    context['most_common_vulnerability'] = VulnerabilityScan.objects.filter(target_domain=id).values(
        "name", "severity").exclude(severity=0).annotate(count=Count('name')).order_by("-count")[:7]
    context['interesting_subdomain'] = get_interesting_subdomains(target=id)
    context['interesting_endpoint'] = get_interesting_endpoint(target=id)
    return render(request, 'target/summary.html', context)

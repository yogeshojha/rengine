import os
import logging
import requests
import itertools
import tempfile
import markdown

from datetime import datetime

from django.template.loader import get_template
from weasyprint import HTML

from django.shortcuts import render, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse, HttpResponseRedirect, HttpResponse
from django.urls import reverse
from django_celery_beat.models import PeriodicTask, IntervalSchedule, ClockedSchedule
from django.utils import timezone
from django.conf import settings
from django.core import serializers
from django.db.models import Count

from startScan.models import *
from targetApp.models import *
from scanEngine.models import EngineType, Configuration
from reNgine.tasks import initiate_scan, create_scan_activity
from reNgine.celery import app

from reNgine.common_func import *


def scan_history(request):
    host = ScanHistory.objects.all().order_by('-start_scan_date')
    context = {'scan_history_active': 'active', "scan_history": host}
    return render(request, 'startScan/history.html', context)


def subscan_history(request):
    subscans = SubScan.objects.all().order_by('-start_scan_date')
    context = {'scan_history_active': 'active', "subscans": subscans}
    return render(request, 'startScan/subscan_history.html', context)


def detail_scan(request, id=None):
    context = {}
    if id:
        context['scan_history_id'] = id
        context['subdomain_count'] = Subdomain.objects.filter(
            scan_history__id=id).values('name').distinct().count()
        context['alive_count'] = Subdomain.objects.filter(
            scan_history__id=id).values('name').distinct().filter(
            http_status__exact=200).count()
        context['important_count'] = Subdomain.objects.filter(
            scan_history__id=id).values('name').distinct().filter(
            is_important=True).count()
        context['scan_activity'] = ScanActivity.objects.filter(
            scan_of__id=id).order_by('time')
        context['endpoint_count'] = EndPoint.objects.filter(
            scan_history__id=id).values('http_url').distinct().count()
        context['endpoint_alive_count'] = EndPoint.objects.filter(
            scan_history__id=id, http_status__exact=200).values('http_url').distinct().count()
        history = get_object_or_404(ScanHistory, id=id)
        context['history'] = history
        vulnerabilities = Vulnerability.objects.filter(scan_history__id=id)
        info_count = vulnerabilities.filter(severity=0).count()
        low_count = vulnerabilities.filter(severity=1).count()
        medium_count = vulnerabilities.filter(severity=2).count()
        high_count = vulnerabilities.filter(severity=3).count()
        critical_count = vulnerabilities.filter(severity=4).count()
        unknown_count = vulnerabilities.filter(severity=-1).count()
        context['vulnerability_list'] = Vulnerability.objects.filter(
            scan_history__id=id).order_by('-severity').all()[:50]
        context['total_vulnerability_count'] = info_count + low_count + \
            medium_count + high_count + critical_count + unknown_count
        context['info_count'] = info_count
        context['low_count'] = low_count
        context['medium_count'] = medium_count
        context['high_count'] = high_count
        context['critical_count'] = critical_count
        context['unknown_count'] = unknown_count
        context['total_vul_ignore_info_count'] = low_count + \
            medium_count + high_count + critical_count
        context['scan_history_active'] = 'active'

        context['scan_engines'] = EngineType.objects.all()

        emails = Email.objects.filter(
            emails__in=ScanHistory.objects.filter(
                id=id))

        context['exposed_count'] = emails.exclude(password__isnull=True).count()

        context['email_count'] = emails.count()

        context['employees_count'] = Employee.objects.filter(
            employees__in=ScanHistory.objects.filter(id=id)).count()

        domain_id = ScanHistory.objects.filter(id=id)

        context['most_recent_scans'] = ScanHistory.objects.filter(domain__id=domain_id[0].domain.id).order_by('-start_scan_date')[:10]

        context['http_status_breakdown'] = Subdomain.objects.filter(scan_history=id).exclude(http_status=0).values('http_status').annotate(Count('http_status'))

        context['most_common_cve'] = CveId.objects.filter(cve_ids__in=Vulnerability.objects.filter(scan_history__id=id)).annotate(nused=Count('cve_ids')).order_by('-nused').values('name', 'nused')[:10]
        context['most_common_cwe'] = CweId.objects.filter(cwe_ids__in=Vulnerability.objects.filter(scan_history__id=id)).annotate(nused=Count('cwe_ids')).order_by('-nused').values('name', 'nused')[:10]
        context['most_common_tags'] = VulnerabilityTags.objects.filter(vuln_tags__in=Vulnerability.objects.filter(scan_history__id=id)).annotate(nused=Count('vuln_tags')).order_by('-nused').values('name', 'nused')[:7]

        context['most_common_vulnerability'] = Vulnerability.objects.exclude(severity=0).filter(scan_history__id=id).values("name", "severity").annotate(count=Count('name')).order_by("-count")[:10]

        context['asset_countries'] = CountryISO.objects.filter(ipaddress__in=IpAddress.objects.filter(ip_addresses__in=Subdomain.objects.filter(scan_history__id=id))).annotate(count=Count('iso')).order_by('-count')

        if domain_id:
            domain_id = domain_id[0].domain.id
            scan_history = ScanHistory.objects.filter(domain=domain_id).filter(subdomain_discovery=True).filter(id__lte=id).filter(scan_status=2)
            if scan_history.count() > 1:
                last_scan = scan_history.order_by('-start_scan_date')[1]
                context['last_scan'] = last_scan

    # badge count for gfs
    if history.used_gf_patterns:
        count_gf = {}
        for gf in history.used_gf_patterns.split(','):
            count_gf[gf] = EndPoint.objects.filter(scan_history__id=id, matched_gf_patterns__icontains=gf).count()
            context['matched_gf_count'] = count_gf
    return render(request, 'startScan/detail_scan.html', context)

def all_subdomains(request):
    context = {}
    context['scan_history_id'] = id
    context['subdomain_count'] = Subdomain.objects.values('name').distinct().count()
    context['alive_count'] = Subdomain.objects.values('name').distinct().filter(
        http_status__exact=200).count()
    context['important_count'] = Subdomain.objects.values('name').distinct().filter(
        is_important=True).count()

    context['scan_engines'] = EngineType.objects.all()

    context['scan_history_active'] = 'active'

    return render(request, 'startScan/subdomains.html', context)

def detail_vuln_scan(request, id=None):
    if id:
        history = get_object_or_404(ScanHistory, id=id)
        context = {'scan_history_id': id, 'history': history}
    else:
        context = {'vuln_scan_active': 'true'}
    return render(request, 'startScan/vulnerabilities.html', context)


def all_endpoints(request):
    context = {}
    context['scan_history_active'] = 'active'
    return render(request, 'startScan/endpoints.html', context)


def start_scan_ui(request, domain_id):
    domain = get_object_or_404(Domain, id=domain_id)
    if request.method == "POST":
        # get imported subdomains
        imported_subdomains = [subdomain.rstrip() for subdomain in request.POST['importSubdomainTextArea'].split('\n')]
        imported_subdomains = [subdomain for subdomain in imported_subdomains if subdomain]

        out_of_scope_subdomains = [subdomain.rstrip() for subdomain in request.POST['outOfScopeSubdomainTextarea'].split('\n')]
        out_of_scope_subdomains = [subdomain for subdomain in out_of_scope_subdomains if subdomain]
        # get engine type
        engine_type = request.POST['scan_mode']
        scan_history_id = create_scan_object(domain_id, engine_type)
        # start the celery task
        celery_task = initiate_scan.apply_async(
            args=(
                domain_id,
                scan_history_id,
                0,
                engine_type,
                imported_subdomains,
                out_of_scope_subdomains
                ))
        ScanHistory.objects.filter(
            id=scan_history_id).update(
            celery_id=celery_task.id)
        messages.add_message(
            request,
            messages.INFO,
            'Scan Started for ' +
            domain.name)
        return HttpResponseRedirect(reverse('scan_history'))
    engine = EngineType.objects.order_by('id')
    custom_engine_count = EngineType.objects.filter(
        default_engine=False).count()
    context = {
        'scan_history_active': 'active',
        'domain': domain,
        'engines': engine,
        'custom_engine_count': custom_engine_count}
    return render(request, 'startScan/start_scan_ui.html', context)


def start_multiple_scan(request):
    # domain = get_object_or_404(Domain, id=host_id)
    if request.method == "POST":
        if request.POST.get('scan_mode', 0):
            # if scan mode is available, then start the scan
            # get engine type
            engine_type = request.POST['scan_mode']
            list_of_domains = request.POST['list_of_domain_id']
            for domain_id in list_of_domains.split(","):
                # start the celery task
                scan_history_id = create_scan_object(domain_id, engine_type)
                celery_task = initiate_scan.apply_async(
                    args=(domain_id, scan_history_id, 0, engine_type))
                ScanHistory.objects.filter(
                    id=scan_history_id).update(
                    celery_id=celery_task.id)
            messages.add_message(
                request,
                messages.INFO,
                'Scan Started for multiple targets')
            return HttpResponseRedirect(reverse('scan_history'))
        else:
            # this else condition will have post request from the scan page
            # containing all the targets id
            list_of_domain_name = []
            list_of_domain_id = []
            for key, value in request.POST.items():
                if key != "list_target_table_length" and key != "csrfmiddlewaretoken":
                    domain = get_object_or_404(Domain, id=value)
                    list_of_domain_name.append(domain.name)
                    list_of_domain_id.append(value)
            domain_ids = ",".join(list_of_domain_id)
    engine = EngineType.objects
    custom_engine_count = EngineType.objects.filter(
        default_engine=False).count()
    context = {
        'scan_history_active': 'active',
        'engines': engine,
        'domain_list': list_of_domain_name,
        'domain_ids': domain_ids,
        'custom_engine_count': custom_engine_count}
    return render(request, 'startScan/start_multiple_scan_ui.html', context)

def export_subdomains(request, scan_id):
    subdomain_list = Subdomain.objects.filter(scan_history__id=scan_id)
    domain_results = ScanHistory.objects.get(id=scan_id)
    response_body = ""
    for name in subdomain_list:
        response_body = response_body + name.name + "\n"
    response = HttpResponse(response_body, content_type='text/plain')
    response['Content-Disposition'] = 'attachment; filename="subdomains_' + \
        domain_results.domain.name + '_' + \
        str(domain_results.start_scan_date.date()) + '.txt"'
    return response


def export_endpoints(request, scan_id):
    endpoint_list = EndPoint.objects.filter(scan_history__id=scan_id)
    domain_results = ScanHistory.objects.get(id=scan_id)
    response_body = ""
    for endpoint in endpoint_list:
        response_body = response_body + endpoint.http_url + "\n"
    response = HttpResponse(response_body, content_type='text/plain')
    response['Content-Disposition'] = 'attachment; filename="endpoints_' + \
        domain_results.domain.name + '_' + \
        str(domain_results.start_scan_date.date()) + '.txt"'
    return response


def export_urls(request, scan_id):
    urls_list = Subdomain.objects.filter(scan_history__id=scan_id)
    domain_results = ScanHistory.objects.get(id=scan_id)
    response_body = ""
    for url in urls_list:
        if url.http_url:
            response_body = response_body + url.http_url + "\n"
    response = HttpResponse(response_body, content_type='text/plain')
    response['Content-Disposition'] = 'attachment; filename="urls_' + \
        domain_results.domain.name + '_' + \
        str(domain_results.start_scan_date.date()) + '.txt"'
    return response


def delete_scan(request, id):
    obj = get_object_or_404(ScanHistory, id=id)
    if request.method == "POST":
        delete_dir = obj.results_dir
        os.system('rm -rf /usr/src/scan_results/' + delete_dir)
        obj.delete()
        messageData = {'status': 'true'}
        messages.add_message(
            request,
            messages.INFO,
            'Scan history successfully deleted!')
    else:
        messageData = {'status': 'false'}
        messages.add_message(
            request,
            messages.INFO,
            'Oops! something went wrong!')
    return JsonResponse(messageData)


def stop_scan(request, id):
    if request.method == "POST":
        scan_history = get_object_or_404(ScanHistory, celery_id=id)
        # stop the celery task
        app.control.revoke(id, terminate=True, signal='SIGKILL')
        scan_history.scan_status = 3
        scan_history.save()
        try:
            last_activity = ScanActivity.objects.filter(
                scan_of=scan_history).order_by('-pk')[0]
            last_activity.status = 0
            last_activity.time = timezone.now()
            last_activity.save()
        except Exception as e:
            print(e)
        create_scan_activity(scan_history, "Scan aborted", 0)
        messageData = {'status': 'true'}
        messages.add_message(
            request,
            messages.INFO,
            'Scan successfully stopped!')
    else:
        messageData = {'status': 'false'}
        messages.add_message(
            request,
            messages.INFO,
            'Oops! something went wrong!')
    return JsonResponse(messageData)


def schedule_scan(request, host_id):
    domain = Domain.objects.get(id=host_id)
    if request.method == "POST":
        # get imported subdomains
        imported_subdomains = [subdomain.rstrip() for subdomain in request.POST['importSubdomainTextArea'].split('\n')]
        imported_subdomains = [subdomain for subdomain in imported_subdomains if subdomain]
        # get engine type
        engine_type = int(request.POST['scan_mode'])
        engine_object = get_object_or_404(EngineType, id=engine_type)
        task_name = engine_object.engine_name + ' for ' + \
            domain.name + \
            ':' + \
            str(datetime.datetime.strftime(timezone.now(), '%Y_%m_%d_%H_%M_%S'))
        if request.POST['scheduled_mode'] == 'periodic':
            # periodic task
            frequency_value = int(request.POST['frequency'])
            frequency_type = request.POST['frequency_type']
            if frequency_type == 'minutes':
                period = IntervalSchedule.MINUTES
            elif frequency_type == 'hours':
                period = IntervalSchedule.HOURS
            elif frequency_type == 'days':
                period = IntervalSchedule.DAYS
            elif frequency_type == 'weeks':
                period = IntervalSchedule.DAYS
                frequency_value *= 7
            elif frequency_type == 'months':
                period = IntervalSchedule.DAYS
                frequency_value *= 30

            schedule, created = IntervalSchedule.objects.get_or_create(
                every=frequency_value,
                period=period,)
            _kwargs = json.dumps({'domain_id': host_id, 'scan_history_id': 0, 'scan_type': 1, 'engine_type': engine_type, 'imported_subdomains': imported_subdomains})
            PeriodicTask.objects.create(interval=schedule,
                                        name=task_name,
                                        task='reNgine.tasks.initiate_scan',
                                        kwargs=_kwargs)
        elif request.POST['scheduled_mode'] == 'clocked':
            # clocked task
            schedule_time = request.POST['scheduled_time']
            clock, created = ClockedSchedule.objects.get_or_create(
                clocked_time=schedule_time,)
            _kwargs = json.dumps({'domain_id': host_id, 'scan_history_id': 0, 'scan_type': 1, 'engine_type': engine_type, 'imported_subdomains': imported_subdomains})
            PeriodicTask.objects.create(clocked=clock,
                                        one_off=True,
                                        name=task_name,
                                        task='reNgine.tasks.initiate_scan',
                                        kwargs=_kwargs)
        messages.add_message(
            request,
            messages.INFO,
            'Scan Scheduled for ' +
            domain.name)
        return HttpResponseRedirect(reverse('scheduled_scan_view'))
    engine = EngineType.objects
    custom_engine_count = EngineType.objects.filter(
        default_engine=False).count()
    context = {
        'scan_history_active': 'active',
        'domain': domain,
        'engines': engine,
        'custom_engine_count': custom_engine_count}
    return render(request, 'startScan/schedule_scan_ui.html', context)


def scheduled_scan_view(request):
    scheduled_tasks = PeriodicTask.objects.all().exclude(name='celery.backend_cleanup')
    context = {
        'scheduled_scan_active': 'active',
        'scheduled_tasks': scheduled_tasks,
    }
    return render(request, 'startScan/schedule_scan_list.html', context)


def delete_scheduled_task(request, id):
    task_object = get_object_or_404(PeriodicTask, id=id)
    if request.method == "POST":
        task_object.delete()
        messageData = {'status': 'true'}
        messages.add_message(
            request,
            messages.INFO,
            'Scheduled Scan successfully deleted!')
    else:
        messageData = {'status': 'false'}
        messages.add_message(
            request,
            messages.INFO,
            'Oops! something went wrong!')
    return JsonResponse(messageData)


def change_scheduled_task_status(request, id):
    if request.method == 'POST':
        task = PeriodicTask.objects.get(id=id)
        task.enabled = not task.enabled
        task.save()
    return HttpResponse('')


def change_vuln_status(request, id):
    if request.method == 'POST':
        vuln = Vulnerability.objects.get(id=id)
        vuln.open_status = not vuln.open_status
        vuln.save()
    return HttpResponse('')


def create_scan_object(host_id, engine_type):
    '''
    create task with pending status so that celery task will execute when
    threads are free
    '''
    # get current time
    current_scan_time = timezone.now()
    # fetch engine and domain object
    engine_object = EngineType.objects.get(pk=engine_type)
    domain = Domain.objects.get(pk=host_id)
    task = ScanHistory()
    task.scan_status = -1
    task.domain = domain
    task.scan_type = engine_object
    task.start_scan_date = current_scan_time
    task.save()
    # save last scan date for domain model
    domain.start_scan_date = current_scan_time
    domain.save()
    return task.id


def delete_all_scan_results(request):
    if request.method == 'POST':
        ScanHistory.objects.all().delete()
        messageData = {'status': 'true'}
        messages.add_message(
            request,
            messages.INFO,
            'All Scan History successfully deleted!')
    return JsonResponse(messageData)

def delete_all_screenshots(request):
    if request.method == 'POST':
        os.system('rm -rf /usr/src/scan_results/*')
        messageData = {'status': 'true'}
        messages.add_message(
            request,
            messages.INFO,
            'Screenshots successfully deleted!')
    return JsonResponse(messageData)


def visualise(request, id):
    scan_history = ScanHistory.objects.get(id=id)
    context = {
        'scan_id': id,
        'scan_history': scan_history,
    }
    return render(request, 'startScan/visualise.html', context)

def start_organization_scan(request, id):
    organization = get_object_or_404(Organization, id=id)
    if request.method == "POST":
        # get engine type
        engine_type = request.POST['scan_mode']
        for domain in organization.get_domains():
            scan_history_id = create_scan_object(domain.id, engine_type)
            # start the celery task
            celery_task = initiate_scan.apply_async(
                args=(domain.id,
                    scan_history_id,
                    0,
                    engine_type,
                    None
                ))
            ScanHistory.objects.filter(
                id=scan_history_id).update(
                celery_id=celery_task.id)
        messages.add_message(
            request,
            messages.INFO,
            'Scan Started for {} domains in organization {}'.format(
                len(organization.get_domains()),
                organization.name
            )
        )
        return HttpResponseRedirect(reverse('scan_history'))
    engine = EngineType.objects.order_by('id')
    custom_engine_count = EngineType.objects.filter(
        default_engine=False).count()
    domain_list = organization.get_domains()
    context = {
        'organization_data_active': 'true',
        'list_organization_li': 'active',
        'organization': organization,
        'engines': engine,
        'domain_list': domain_list,
        'custom_engine_count': custom_engine_count}
    return render(request, 'organization/start_scan.html', context)

def schedule_organization_scan(request, id):
    organization =Organization.objects.get(id=id)
    if request.method == "POST":
        # get engine type
        engine_type = int(request.POST['scan_mode'])
        engine_object = get_object_or_404(EngineType, id=engine_type)
        for domain in organization.get_domains():
            task_name = engine_object.engine_name + ' for ' + \
                domain.name + \
                ':' + \
                str(datetime.datetime.strftime(
                    timezone.now(),
                    '%Y_%m_%d_%H_%M_%S'
                ))
            if request.POST['scheduled_mode'] == 'periodic':
                # periodic task
                frequency_value = int(request.POST['frequency'])
                frequency_type = request.POST['frequency_type']
                if frequency_type == 'minutes':
                    period = IntervalSchedule.MINUTES
                elif frequency_type == 'hours':
                    period = IntervalSchedule.HOURS
                elif frequency_type == 'days':
                    period = IntervalSchedule.DAYS
                elif frequency_type == 'weeks':
                    period = IntervalSchedule.DAYS
                    frequency_value *= 7
                elif frequency_type == 'months':
                    period = IntervalSchedule.DAYS
                    frequency_value *= 30

                schedule, created = IntervalSchedule.objects.get_or_create(
                    every=frequency_value,
                    period=period,)
                _kwargs = json.dumps({'domain_id': domain.id,
                        'scan_history_id': 0,
                        'scan_type': 1,
                        'engine_type': engine_type,
                        'imported_subdomains': None
                })
                PeriodicTask.objects.create(interval=schedule,
                    name=task_name,
                    task='reNgine.tasks.initiate_scan',
                    kwargs=_kwargs
                )
            elif request.POST['scheduled_mode'] == 'clocked':
                # clocked task
                schedule_time = request.POST['scheduled_time']
                clock, created = ClockedSchedule.objects.get_or_create(
                    clocked_time=schedule_time,)
                _kwargs = json.dumps({'domain_id': domain.id,
                    'scan_history_id': 0,
                    'scan_type': 1,
                    'engine_type': engine_type,
                    'imported_subdomains': None}
                )
                PeriodicTask.objects.create(clocked=clock,
                    one_off=True,
                    name=task_name,
                    task='reNgine.tasks.initiate_scan',
                    kwargs=_kwargs
                )
        messages.add_message(
            request,
            messages.INFO,
            'Scan Started for {} domains in organization {}'.format(
                len(organization.get_domains()),
                organization.name
            )
        )
        return HttpResponseRedirect(reverse('scheduled_scan_view'))
    engine = EngineType.objects
    custom_engine_count = EngineType.objects.filter(
        default_engine=False).count()
    context = {
        'scan_history_active': 'active',
        'organization': organization,
        'domain_list': organization.get_domains(),
        'engines': engine,
        'custom_engine_count': custom_engine_count}
    return render(request, 'organization/schedule_scan_ui.html', context)


def delete_scans(request):
    context = {}
    if request.method == "POST":
        list_of_scan_id = []

        for key, value in request.POST.items():
            if key != "scan_history_table_length" and key != "csrfmiddlewaretoken":
                obj = get_object_or_404(ScanHistory, id=value)
                delete_dir = obj.results_dir
                os.system('rm -rf /usr/src/scan_results/' + delete_dir)
                obj.delete()
        messages.add_message(
            request,
            messages.INFO,
            'All Scans deleted!')
    return HttpResponseRedirect(reverse('scan_history'))


def customize_report(request, id):
    scan_history = ScanHistory.objects.get(id=id)
    context = {
        'scan_id': id,
        'scan_history': scan_history,
    }
    return render(request, 'startScan/customize_report.html', context)


def create_report(request, id):
    primary_color = '#FFB74D'
    secondary_color = '#212121'

    # get report type
    report_type = request.GET['report_type'] if 'report_type' in request.GET  else 'full'

    if report_type == 'recon':
        show_recon = True
        show_vuln = False
        report_name = 'Reconnaissance Report'
    elif report_type == 'vulnerability':
        show_recon = False
        show_vuln = True
        report_name = 'Vulnerability Report'
    else:
        # default
        show_recon = True
        show_vuln = True
        report_name = 'Full Scan Report'

    scan_object = ScanHistory.objects.get(id=id)
    unique_vulnerabilities = Vulnerability.objects.filter(scan_history=scan_object).values("name", "severity").annotate(count=Count('name')).order_by('-severity', '-count')
    all_vulnerabilities = Vulnerability.objects.filter(scan_history=scan_object).order_by('-severity')
    subdomains = Subdomain.objects.filter(scan_history=scan_object).order_by('-content_length')
    subdomain_alive_count = Subdomain.objects.filter(
        scan_history__id=id).values('name').distinct().filter(
        http_status__exact=200).count()
    interesting_subdomains = get_interesting_subdomains(scan_history=id)
    ip_addresses = IpAddress.objects.filter(
        ip_addresses__in=Subdomain.objects.filter(
            scan_history__id=id)).distinct()

    data = {
        'scan_object': scan_object,
        'unique_vulnerabilities': unique_vulnerabilities,
        'all_vulnerabilities': all_vulnerabilities,
        'subdomain_alive_count': subdomain_alive_count,
        'interesting_subdomains': interesting_subdomains,
        'subdomains': subdomains,
        'ip_addresses': ip_addresses,
        'show_recon': show_recon,
        'show_vuln': show_vuln,
        'report_name': report_name,
    }

    # get report related config
    if VulnerabilityReportSetting.objects.all().exists():
        report = VulnerabilityReportSetting.objects.all()[0]
        data['company_name'] = report.company_name
        data['company_address'] = report.company_address
        data['company_email'] = report.company_email
        data['company_website'] = report.company_website
        data['show_rengine_banner'] = report.show_rengine_banner
        data['show_footer'] = report.show_footer
        data['footer_text'] = report.footer_text
        data['show_executive_summary'] = report.show_executive_summary

        primary_color = report.primary_color
        secondary_color = report.secondary_color

        description = report.executive_summary_description

        # replace executive_summary_description with template syntax!
        description = description.replace('{scan_date}', scan_object.start_scan_date.strftime('%d %B, %Y'))
        description = description.replace('{company_name}', report.company_name)
        description = description.replace('{target_name}', scan_object.domain.name)
        if scan_object.domain.description:
            description = description.replace('{target_description}', scan_object.domain.description)
        description = description.replace('{subdomain_count}', str(subdomains.count()))
        description = description.replace('{vulnerability_count}', str(all_vulnerabilities.count()))
        description = description.replace('{critical_count}', str(all_vulnerabilities.filter(severity=4).count()))
        description = description.replace('{high_count}', str(all_vulnerabilities.filter(severity=3).count()))
        description = description.replace('{medium_count}', str(all_vulnerabilities.filter(severity=2).count()))
        description = description.replace('{low_count}', str(all_vulnerabilities.filter(severity=1).count()))
        description = description.replace('{info_count}', str(all_vulnerabilities.filter(severity=0).count()))
        description = description.replace('{unknown_count}', str(all_vulnerabilities.filter(severity=-1).count()))

        # convert to html
        data['executive_summary_description'] = markdown.markdown(description)

    data['primary_color'] = primary_color
    data['secondary_color'] = secondary_color

    template = get_template('report/template.html')
    html = template.render(data)
    pdf = HTML(string=html).write_pdf()

    if 'download' in request.GET:
        response = HttpResponse(pdf, content_type='application/octet-stream')
    else:
        response = HttpResponse(pdf, content_type='application/pdf')

    return response

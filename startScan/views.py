from django.shortcuts import render, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse, HttpResponseRedirect, HttpResponse
from django.urls import reverse
from startScan.models import ScanHistory, ScannedHost, ScanActivity, WayBackEndPoint, VulnerabilityScan
from django_celery_beat.models import PeriodicTask, IntervalSchedule, ClockedSchedule
from notification.models import NotificationHooks
from targetApp.models import Domain
from scanEngine.models import EngineType, Configuration
from django.utils import timezone
from django.conf import settings
from datetime import datetime
from reNgine.tasks import doScan
from reNgine.celery import app
import os
import requests


def scan_history(request):
    host = ScanHistory.objects.all().order_by('-last_scan_date')
    context = {'scan_history_active': 'true', "scan_history": host}
    return render(request, 'startScan/history.html', context)


def detail_scan(request, id=None):
    if id:
        subdomain_count = ScannedHost.objects.filter(scan_history__id=id).count()
        alive_count = ScannedHost.objects.filter(
            scan_history__id=id).exclude(
            http_status__exact=0).count()
        scan_activity = ScanActivity.objects.filter(
            scan_of__id=id).order_by('time')
        endpoint_count = WayBackEndPoint.objects.filter(url_of__id=id).count()
        endpoint_alive_count = WayBackEndPoint.objects.filter(
            url_of__id=id, http_status__exact=200).count()
        history = get_object_or_404(ScanHistory, id=id)
        info_count = VulnerabilityScan.objects.filter(
            vulnerability_of__id=id, severity=0).count()
        low_count = VulnerabilityScan.objects.filter(
            vulnerability_of__id=id, severity=1).count()
        medium_count = VulnerabilityScan.objects.filter(
            vulnerability_of__id=id, severity=2).count()
        high_count = VulnerabilityScan.objects.filter(
            vulnerability_of__id=id, severity=3).count()
        critical_count = VulnerabilityScan.objects.filter(
            vulnerability_of__id=id, severity=4).count()
        total_vulnerability_count = info_count + low_count + \
            medium_count + high_count + critical_count
        context = {'scan_history_active': 'true',
                   'scan_history': scan_history,
                   'scan_activity': scan_activity,
                   'alive_count': alive_count,
                   'scan_history_id': id,
                   'subdomain_count': subdomain_count,
                   'endpoint_count': endpoint_count,
                   'endpoint_alive_count': endpoint_alive_count,
                   'history': history,
                   'info_count': info_count,
                   'low_count': low_count,
                   'medium_count': medium_count,
                   'high_count': high_count,
                   'critical_count': critical_count,
                   'total_vulnerability_count': total_vulnerability_count,
                   }
    else:
        context = {}
    return render(request, 'startScan/detail_scan.html', context)


def detail_vuln_scan(request, id=None):
    if id:
        history = get_object_or_404(ScanHistory, id=id)
        context = {'scan_history_id': id, 'history': history}
    else:
        context = {'vuln_scan_active': 'true'}
    return render(request, 'startScan/detail_vuln_scan.html', context)


def detail_endpoint_scan(request, id=None):
    if id:
        history = get_object_or_404(ScanHistory, id=id)
        context = {'scan_history_id': id, 'history': history}
    else:
        context = {}
    return render(request, 'startScan/detail_endpoint_scan.html', context)


def start_scan_ui(request, host_id):
    domain = get_object_or_404(Domain, id=host_id)
    if request.method == "POST":
        # get engine type
        engine_type = request.POST['scan_mode']
        scan_history_id = create_scan_object(host_id, engine_type)
        # start the celery task
        celery_task = doScan.apply_async(
            args=(host_id, scan_history_id, 0, None))
        ScanHistory.objects.filter(
            id=scan_history_id).update(
            celery_id=celery_task.id)
        messages.add_message(
            request,
            messages.INFO,
            'Scan Started for ' +
            domain.domain_name)
        return HttpResponseRedirect(reverse('scan_history'))
    engine = EngineType.objects.order_by('id')
    custom_engine_count = EngineType.objects.filter(
        default_engine=False).count()
    context = {
        'scan_history_active': 'true',
        'domain': domain,
        'engines': engine,
        'custom_engine_count': custom_engine_count}
    return render(request, 'startScan/start_scan_ui.html', context)


def start_multiple_scan(request):
    # domain = get_object_or_404(Domain, id=host_id)
    domain_text = ""
    if request.method == "POST":
        if request.POST.get('scan_mode', 0):
            # if scan mode is available, then start the scan
            # get engine type
            engine_type = request.POST['scan_mode']
            list_of_domains = request.POST['list_of_domain_id']
            for domain_id in list_of_domains.split(","):
                # start the celery task
                scan_history_id = create_scan_object(domain_id, engine_type)
                celery_task = doScan.apply_async(
                    args=(domain_id, scan_history_id, 0, None))
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
                if key != "style-2_length" and key != "csrfmiddlewaretoken":
                    domain = get_object_or_404(Domain, id=value)
                    list_of_domain_name.append(domain.domain_name)
                    list_of_domain_id.append(value)
            domain_text = ", ".join(list_of_domain_name)
            domain_ids = ",".join(list_of_domain_id)
    engine = EngineType.objects
    custom_engine_count = EngineType.objects.filter(
        default_engine=False).count()
    context = {
        'scan_history_active': 'true',
        'engines': engine,
        'domain_list': domain_text,
        'domain_ids': domain_ids,
        'custom_engine_count': custom_engine_count}
    return render(request, 'startScan/start_multiple_scan_ui.html', context)


def export_subdomains(request, scan_id):
    subdomain_list = ScannedHost.objects.filter(scan_history__id=scan_id)
    domain_results = ScanHistory.objects.get(id=scan_id)
    response_body = ""
    for subdomain in subdomain_list:
        response_body = response_body + subdomain.subdomain + "\n"
    response = HttpResponse(response_body, content_type='text/plain')
    response['Content-Disposition'] = 'attachment; filename="subdomains_' + \
        domain_results.domain_name.domain_name + '_' + \
        str(domain_results.last_scan_date.date()) + '.txt"'
    return response


def export_endpoints(request, scan_id):
    endpoint_list = WayBackEndPoint.objects.filter(url_of__id=scan_id)
    domain_results = ScanHistory.objects.get(id=scan_id)
    response_body = ""
    for endpoint in endpoint_list:
        response_body = response_body + endpoint.http_url + "\n"
    response = HttpResponse(response_body, content_type='text/plain')
    response['Content-Disposition'] = 'attachment; filename="endpoints_' + \
        domain_results.domain_name.domain_name + '_' + \
        str(domain_results.last_scan_date.date()) + '.txt"'
    return response


def export_urls(request, scan_id):
    urls_list = ScannedHost.objects.filter(scan_history__id=scan_id)
    domain_results = ScanHistory.objects.get(id=scan_id)
    response_body = ""
    for url in urls_list:
        if url.http_url:
            response_body = response_body + url.http_url + "\n"
    response = HttpResponse(response_body, content_type='text/plain')
    response['Content-Disposition'] = 'attachment; filename="urls_' + \
        domain_results.domain_name.domain_name + '_' + \
        str(domain_results.last_scan_date.date()) + '.txt"'
    return response


def delete_scan(request, id):
    obj = get_object_or_404(ScanHistory, id=id)
    if request.method == "POST":
        delete_dir = obj.domain_name.domain_name + '_' + \
            str(datetime.strftime(obj.last_scan_date, '%Y_%m_%d_%H_%M_%S'))
        delete_path = settings.TOOL_LOCATION + 'scan_results/' + delete_dir
        os.system('rm -rf ' + delete_path)
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
    obj = get_object_or_404(ScanHistory, celery_id=id)
    if request.method == "POST":
        # stop the celery task
        app.control.revoke(id, terminate=True, signal='SIGKILL')
        obj.scan_status = 3
        obj.save()
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
        # get engine type
        engine_type = int(request.POST['scan_mode'])
        engine_object = get_object_or_404(EngineType, id=engine_type)
        task_name = engine_object.engine_name + ' for ' + \
            domain.domain_name + \
            ':' + \
            str(datetime.strftime(timezone.now(), '%Y_%m_%d_%H_%M_%S'))
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
            PeriodicTask.objects.create(interval=schedule,
                                        name=task_name,
                                        task='reNgine.tasks.doScan',
                                        args=[host_id, 0, 1, engine_type])
        elif request.POST['scheduled_mode'] == 'clocked':
            # clocked task
            schedule_time = request.POST['scheduled_time']
            clock, created = ClockedSchedule.objects.get_or_create(
                clocked_time=schedule_time,)
            PeriodicTask.objects.create(clocked=clock,
                                        one_off=True,
                                        name=task_name,
                                        task='reNgine.tasks.doScan',
                                        args=[host_id, 0, 1, engine_type])
        messages.add_message(
            request,
            messages.INFO,
            'Scan Scheduled for ' +
            domain.domain_name)
        return HttpResponseRedirect(reverse('scheduled_scan_view'))
    engine = EngineType.objects
    custom_engine_count = EngineType.objects.filter(
        default_engine=False).count()
    context = {
        'scan_history_active': 'true',
        'domain': domain,
        'engines': engine,
        'custom_engine_count': custom_engine_count}
    return render(request, 'startScan/schedule_scan_ui.html', context)


def scheduled_scan_view(request):
    scheduled_tasks = PeriodicTask.objects.all().exclude(name='celery.backend_cleanup')
    context = {
        'scheduled_scan_active': 'true',
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
        vuln = VulnerabilityScan.objects.get(id=id)
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
    task.domain_name = domain
    task.scan_type = engine_object
    task.last_scan_date = current_scan_time
    task.save()
    # save last scan date for domain model
    domain.last_scan_date = current_scan_time
    domain.save()
    return task.id

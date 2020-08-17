from django.shortcuts import render, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse, HttpResponseRedirect, HttpResponse
from django.urls import reverse
from startScan.models import ScanHistory, ScannedHost, ScanActivity, WayBackEndPoint
from django_celery_beat.models import PeriodicTask, IntervalSchedule
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


def index(request):
    return render(request, 'startScan/index.html')


def scan_history(request):
    host = ScanHistory.objects.all().order_by('-last_scan_date')
    context = {'scan_history_active': 'true', "scan_history": host}
    return render(request, 'startScan/history.html', context)


def detail_scan(request, id):
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
    context = {'scan_history_active': 'true',
               'scan_history': scan_history,
               'scan_activity': scan_activity,
               'alive_count': alive_count,
               'scan_history_id': id,
               'subdomain_count': subdomain_count,
               'endpoint_count': endpoint_count,
               'endpoint_alive_count': endpoint_alive_count,
               'history': history,
               }
    return render(request, 'startScan/detail_scan.html', context)


def start_scan_ui(request, host_id):
    domain = get_object_or_404(Domain, id=host_id)
    if request.method == "POST":
        # get engine type
        engine_type = request.POST['scan_mode']
        # start the celery task
        celery_task = doScan.delay(host_id, engine_type)
        messages.add_message(
            request,
            messages.INFO,
            'Scan Started for ' +
            domain.domain_name)
        return HttpResponseRedirect(reverse('scan_history'))
    engine = EngineType.objects
    custom_engine_count = EngineType.objects.filter(
        default_engine=False).count()
    context = {
        'scan_history_active': 'true',
        'domain': domain,
        'engines': engine,
        'custom_engine_count': custom_engine_count}
    return render(request, 'startScan/start_scan_ui.html', context)


def schedule_scan(request, host_id):
    domain = get_object_or_404(Domain, id=host_id)
    if request.method == "POST":
        # get engine type
        engine_type = int(request.POST['scan_mode'])
        engine_object = get_object_or_404(EngineType, id=engine_type)
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

            task_name = engine_object.engine_name + ' for ' + \
                domain.domain_name + \
                ':' + \
                str(datetime.strftime(timezone.now(), '%Y_%m_%d_%H_%M_%S'))

            schedule, created = IntervalSchedule.objects.get_or_create(
                                            every=frequency_value,
                                            period=period,)
            PeriodicTask.objects.create(interval=schedule,
                                        name=task_name,
                                        task='reNgine.tasks.doScan',
                                        args=[host_id, engine_type])
        elif request.POST['scheduled_mode'] == 'clocked':
            # clocked task
            pass
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

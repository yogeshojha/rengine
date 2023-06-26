import json
import logging

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.db.models import Count
from django.db.models.functions import TruncDay
from django.dispatch import receiver
from django.shortcuts import redirect, render
from django.utils import timezone
from django.http import HttpResponseRedirect, JsonResponse
from django.urls import reverse
from rolepermissions.roles import assign_role, clear_roles
from rolepermissions.decorators import has_permission_decorator

from startScan.models import *
from targetApp.models import Domain
from dashboard.models import Project
from reNgine.definitions import *


logger = logging.getLogger(__name__)

def index(request, slug):
    try:
        project = Project.objects.get(slug=slug)
    except Exception as e:
        # if project not found redirect to 404
        return HttpResponseRedirect(reverse('four_oh_four'))

    domains = Domain.objects.filter(project=project)
    subdomains = Subdomain.objects.filter(target_domain__project=project)
    endpoints = EndPoint.objects.filter(target_domain__project=project)
    scan_histories = ScanHistory.objects.filter(domain__project=project)
    vulnerabilities = Vulnerability.objects.filter(target_domain__project=project)
    scan_activities = ScanActivity.objects.filter(scan_of__in=scan_histories)

    domain_count = domains.count()
    endpoint_count = endpoints.count()
    scan_count = scan_histories.count()
    subdomain_count = subdomains.count()
    subdomain_with_ip_count = subdomains.filter(ip_addresses__isnull=False).count()
    alive_count = subdomains.exclude(http_status__exact=0).count()
    endpoint_alive_count = endpoints.filter(http_status__exact=200).count()

    info_count = vulnerabilities.filter(severity=0).count()
    low_count = vulnerabilities.filter(severity=1).count()
    medium_count = vulnerabilities.filter(severity=2).count()
    high_count = vulnerabilities.filter(severity=3).count()
    critical_count = vulnerabilities.filter(severity=4).count()
    unknown_count = vulnerabilities.filter(severity=-1).count()

    vulnerability_feed = vulnerabilities.order_by('-discovered_date')[:20]
    activity_feed = scan_activities.order_by('-time')[:20]
    total_vul_count = info_count + low_count + \
        medium_count + high_count + critical_count + unknown_count
    total_vul_ignore_info_count = low_count + \
        medium_count + high_count + critical_count
    most_common_vulnerability = Vulnerability.objects.values("name", "severity").annotate(count=Count('name')).order_by("-count")[:10]
    last_week = timezone.now() - timedelta(days=7)

    count_targets_by_date = Domain.objects.filter(
        insert_date__gte=last_week).annotate(
        date=TruncDay('insert_date')).values("date").annotate(
            created_count=Count('id')).order_by("-date")
    count_subdomains_by_date = Subdomain.objects.filter(
        discovered_date__gte=last_week).annotate(
        date=TruncDay('discovered_date')).values("date").annotate(
            count=Count('id')).order_by("-date")
    count_vulns_by_date = Vulnerability.objects.filter(
        discovered_date__gte=last_week).annotate(
        date=TruncDay('discovered_date')).values("date").annotate(
            count=Count('id')).order_by("-date")
    count_scans_by_date = ScanHistory.objects.filter(
        start_scan_date__gte=last_week).annotate(
        date=TruncDay('start_scan_date')).values("date").annotate(
            count=Count('id')).order_by("-date")
    count_endpoints_by_date = EndPoint.objects.filter(
        discovered_date__gte=last_week).annotate(
        date=TruncDay('discovered_date')).values("date").annotate(
            count=Count('id')).order_by("-date")

    last_7_dates = [(timezone.now() - timedelta(days=i)).date()
                    for i in range(0, 7)]

    targets_in_last_week = []
    subdomains_in_last_week = []
    vulns_in_last_week = []
    scans_in_last_week = []
    endpoints_in_last_week = []

    for date in last_7_dates:
        _target = count_targets_by_date.filter(date=date)
        _subdomain = count_subdomains_by_date.filter(date=date)
        _vuln = count_vulns_by_date.filter(date=date)
        _scan = count_scans_by_date.filter(date=date)
        _endpoint = count_endpoints_by_date.filter(date=date)
        if _target:
            targets_in_last_week.append(_target[0]['created_count'])
        else:
            targets_in_last_week.append(0)
        if _subdomain:
            subdomains_in_last_week.append(_subdomain[0]['count'])
        else:
            subdomains_in_last_week.append(0)
        if _vuln:
            vulns_in_last_week.append(_vuln[0]['count'])
        else:
            vulns_in_last_week.append(0)
        if _scan:
            scans_in_last_week.append(_scan[0]['count'])
        else:
            scans_in_last_week.append(0)
        if _endpoint:
            endpoints_in_last_week.append(_endpoint[0]['count'])
        else:
            endpoints_in_last_week.append(0)

    targets_in_last_week.reverse()
    subdomains_in_last_week.reverse()
    vulns_in_last_week.reverse()
    scans_in_last_week.reverse()
    endpoints_in_last_week.reverse()

    context = {
        'dashboard_data_active': 'active',
        'domain_count': domain_count,
        'endpoint_count': endpoint_count,
        'scan_count': scan_count,
        'subdomain_count': subdomain_count,
        'subdomain_with_ip_count': subdomain_with_ip_count,
        'alive_count': alive_count,
        'endpoint_alive_count': endpoint_alive_count,
        'info_count': info_count,
        'low_count': low_count,
        'medium_count': medium_count,
        'high_count': high_count,
        'critical_count': critical_count,
        'unknown_count': unknown_count,
        'most_common_vulnerability': most_common_vulnerability,
        'total_vul_count': total_vul_count,
        'total_vul_ignore_info_count': total_vul_ignore_info_count,
        'vulnerability_feed': vulnerability_feed,
        'activity_feed': activity_feed,
        'targets_in_last_week': targets_in_last_week,
        'subdomains_in_last_week': subdomains_in_last_week,
        'vulns_in_last_week': vulns_in_last_week,
        'scans_in_last_week': scans_in_last_week,
        'endpoints_in_last_week': endpoints_in_last_week,
        'last_7_dates': last_7_dates,
    }

    context['total_ips'] = IpAddress.objects.all().count()
    context['most_used_port'] = Port.objects.annotate(count=Count('ports')).order_by('-count')[:7]
    context['most_used_ip'] = IpAddress.objects.annotate(count=Count('ip_addresses')).order_by('-count').exclude(ip_addresses__isnull=True)[:7]
    context['most_used_tech'] = Technology.objects.annotate(count=Count('technologies')).order_by('-count')[:7]

    context['most_common_cve'] = CveId.objects.annotate(nused=Count('cve_ids')).order_by('-nused').values('name', 'nused')[:7]
    context['most_common_cwe'] = CweId.objects.annotate(nused=Count('cwe_ids')).order_by('-nused').values('name', 'nused')[:7]
    context['most_common_tags'] = VulnerabilityTags.objects.annotate(nused=Count('vuln_tags')).order_by('-nused').values('name', 'nused')[:7]

    context['asset_countries'] = CountryISO.objects.annotate(count=Count('ipaddress')).order_by('-count')

    return render(request, 'dashboard/index.html', context)


def profile(request, slug):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(
                request,
                'Your password was successfully changed!')
            return redirect('profile')
        else:
            messages.error(request, 'Please correct the error below.')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'dashboard/profile.html', {
        'form': form
    })


@has_permission_decorator(PERM_MODIFY_SYSTEM_CONFIGURATIONS, redirect_url=FOUR_OH_FOUR_URL)
def admin_interface(request):
    UserModel = get_user_model()
    users = UserModel.objects.all().order_by('date_joined')
    return render(
        request,
        'dashboard/admin.html',
        {
            'users': users
        }
    )

@has_permission_decorator(PERM_MODIFY_SYSTEM_CONFIGURATIONS, redirect_url=FOUR_OH_FOUR_URL)
def admin_interface_update(request):
    mode = request.GET.get('mode')
    user_id = request.GET.get('user')
    if user_id:
        UserModel = get_user_model()
        user = UserModel.objects.get(id=user_id)
    if request.method == 'GET':
        if mode == 'change_status':
            user.is_active = not user.is_active
            user.save()
    elif request.method == 'POST':
        if mode == 'delete':
            try:
                user.delete()
                messages.add_message(
                request,
                messages.INFO,
                    f'User {user.username} successfully deleted.'
                )
                messageData = {'status': True}
            except Exception as e:
                logger.error(e)
                messageData = {'status': False}
        elif mode == 'update':
            try:
                response = json.loads(request.body)
                role = response.get('role')
                change_password = response.get('change_password')
                clear_roles(user)
                assign_role(user, role)
                if change_password:
                    user.set_password(change_password)
                    user.save()
                messageData = {'status': True}
            except Exception as e:
                logger.error(e)
                messageData = {'status': False, 'error': str(e)}
        elif mode == 'create':
            try:
                response = json.loads(request.body)
                UserModel = get_user_model()
                user = UserModel.objects.create_user(
                    username=response.get('username'),
                    password=response.get('password')
                )
                assign_role(user, response.get('role'))
                messageData = {'status': True}
            except Exception as e:
                logger.error(e)
                messageData = {'status': False, 'error': str(e)}
        return JsonResponse(messageData)
    return HttpResponseRedirect(reverse('admin_interface'))


@receiver(user_logged_out)
def on_user_logged_out(sender, request, **kwargs):
    messages.add_message(
        request,
        messages.INFO,
        'You have been successfully logged out. Thank you ' +
        'for using reNgine.')


@receiver(user_logged_in)
def on_user_logged_in(sender, request, **kwargs):
    messages.add_message(
        request,
        messages.INFO,
        'Hi @' +
        request.user.username +
        ' welcome back!')


def search(request):
    return render(request, 'dashboard/search.html')


def four_oh_four(request):
    return render(request, '404.html')

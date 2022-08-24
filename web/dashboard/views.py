from datetime import timedelta

from targetApp.models import Domain
from startScan.models import *

from django.utils import timezone
from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.db.models.functions import TruncDay
from django.contrib.auth.decorators import login_required
from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_out, user_logged_in
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.db.models import Count, Value, CharField, Q


def index(request):
    domain_count = Domain.objects.all().count()
    endpoint_count = EndPoint.objects.all().count()
    scan_count = ScanHistory.objects.all().count()
    subdomain_count = Subdomain.objects.all().count()
    subdomain_with_ip_count = Subdomain.objects.filter(ip_addresses__isnull=False).count()
    alive_count = \
        Subdomain.objects.all().exclude(http_status__exact=0).count()
    endpoint_alive_count = \
        EndPoint.objects.filter(http_status__exact=200).count()

    vulnerabilities = Vulnerability.objects.all()
    info_count = vulnerabilities.filter(severity=0).count()
    low_count = vulnerabilities.filter(severity=1).count()
    medium_count = vulnerabilities.filter(severity=2).count()
    high_count = vulnerabilities.filter(severity=3).count()
    critical_count = vulnerabilities.filter(severity=4).count()
    unknown_count = vulnerabilities.filter(severity=-1).count()

    vulnerability_feed = Vulnerability.objects.all().order_by(
        '-discovered_date')[:20]
    activity_feed = ScanActivity.objects.all().order_by('-time')[:20]
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


def profile(request):
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

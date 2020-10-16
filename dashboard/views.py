from django.shortcuts import render, redirect
from django.http import HttpResponse
from startScan.models import ScanHistory, WayBackEndPoint, ScannedHost, VulnerabilityScan
from targetApp.models import Domain
from django.contrib.auth.decorators import login_required
from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_out, user_logged_in
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm


def index(request):
    domain_count = Domain.objects.all().count()
    endpoint_count = WayBackEndPoint.objects.all().count()
    scan_count = ScanHistory.objects.all().count()
    subdomain_count = ScannedHost.objects.all().count()
    alive_count = \
        ScannedHost.objects.all().exclude(http_status__exact=0).count()
    endpoint_alive_count = \
        WayBackEndPoint.objects.filter(http_status__exact=200).count()
    on_going_scan_count = \
        ScanHistory.objects.filter(scan_status=1).count()
    recent_scans = ScanHistory.objects.all().order_by(
        '-last_scan_date').exclude(scan_status=-1)[:4]
    upcoming_scans = ScanHistory.objects.filter(scan_status=-1)[:4]
    info_count = VulnerabilityScan.objects.filter(severity=0).count()
    low_count = VulnerabilityScan.objects.filter(severity=1).count()
    medium_count = VulnerabilityScan.objects.filter(severity=2).count()
    high_count = VulnerabilityScan.objects.filter(severity=3).count()
    critical_count = VulnerabilityScan.objects.filter(severity=4).count()
    context = {
        'dashboard_data_active': 'true',
        'domain_count': domain_count,
        'endpoint_count': endpoint_count,
        'scan_count': scan_count,
        'subdomain_count': subdomain_count,
        'alive_count': alive_count,
        'endpoint_alive_count': endpoint_alive_count,
        'on_going_scan_count': on_going_scan_count,
        'recent_scans': recent_scans,
        'upcoming_scans': upcoming_scans,
        'info_count': info_count,
        'low_count': low_count,
        'medium_count': medium_count,
        'high_count': high_count,
        'critical_count': critical_count,
        }
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

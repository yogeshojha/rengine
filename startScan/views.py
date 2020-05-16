from django.shortcuts import render, get_object_or_404
from django.contrib import messages
from django import http
from django.urls import reverse
from .models import ScanHistory, ScannedSubdomains

def index(request):
    return render(request, 'startScan/index.html')

def scan_history(request):
    scan_history = ScanHistory.objects
    context = {'scan_history_active': 'true', "scan_history":scan_history}
    return render(request, 'startScan/history.html', context)

def detail_scan(request, id):
    subdomain_details = ScannedSubdomains.objects.filter(scan_history__id=id)
    context = {'scan_history_active': 'true', 'subdomain':subdomain_details}
    return render(request, 'startScan/detail_scan.html', context)

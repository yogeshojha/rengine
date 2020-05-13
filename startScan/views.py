from django.shortcuts import render, get_object_or_404
from django.contrib import messages
from django import http
from django.urls import reverse
from .models import ScanHistoryModel

def index(request):
    return render(request, 'startScan/index.html')

def scan_history(request):
    scan_history = ScanHistoryModel.objects
    context = {'scan_history_active': 'true', "scan_history":scan_history}
    return render(request, 'startScan/history.html', context)

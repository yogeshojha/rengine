from django.shortcuts import render, get_object_or_404
from scanEngine.models import EngineType
from scanEngine.forms import AddEngineForm
from django.contrib import messages
from django import http
from django.urls import reverse

def index(request):
    return render(request, 'startScan/index.html')

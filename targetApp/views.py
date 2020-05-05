from django.shortcuts import render
from django.http import HttpResponse

def index(request):
    # TODO bring default target page
    return render(request, 'target/index.html')

def addTarget(request):
    return render(request, 'target/add.html')

def listTarget(request):
    return render(request, 'target/list.html')

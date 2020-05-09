from django.shortcuts import render
from django.http import HttpResponse

def index(request):
    context = {"dashboard_data_active": "true"}
    return render(request, 'dashboard/index.html', context)

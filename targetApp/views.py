from django.shortcuts import render
from django.http import HttpResponse
from .models import Domain
from django.contrib import messages


def index(request):
    # TODO bring default target page
    return render(request, 'target/index.html')

def add_target_form(request):
    return render(request, 'target/add.html')

def list_target(request):
    return render(request, 'target/list.html')

def add_target_db(request):
    if request.method == "POST":
        domain = Domain()
        domain.domain_name = request.POST.get('domainName')
        domain.domain_description = request.POST.get('domainDescription')
        domain.save_domain()

    messages.add_message(request, messages.INFO, 'Target domain ' + domain.domain_name + ' added successfully')
    return render(request, 'target/add.html')

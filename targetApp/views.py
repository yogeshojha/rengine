from django.shortcuts import render
from django.http import HttpResponse
from .models import Domain
from django.contrib import messages
# import validators

def index(request):
    # TODO bring default target page
    return render(request, 'target/index.html')

def add_target_form(request):
    if request.method == "POST":
        domain = Domain()
        domain.domain_name = request.POST.get('domainName')
        domain.domain_description = request.POST.get('domainDescription')
        # if validators.domain(domain_name):
        #     domain.save_domain()
        #     messages.add_message(request, messages.INFO, 'Target domain ' + domain.domain_name + ' added successfully')
        # else:
        #     messages.add_message(request, messages.ERROR, 'Target domain ' + domain.domain_name + ' is not a valid domain!')
    context = {"add_target_li": "active", "target_data_active": "true"}
    return render(request, 'target/add.html', context)

def list_target(request):
    context = {"list_target_li": "active", "target_data_active": "true"}
    return render(request, 'target/list.html', context)

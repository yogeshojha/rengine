from django.shortcuts import render
from django import http
from .models import Domain
from django.contrib import messages
from .forms import AddDomainForm, RawDomainForm
from django.utils import timezone
from django.urls import reverse

def index(request):
    # TODO bring default target page
    return render(request, 'target/index.html')

def add_target_form(request):
    form = RawDomainForm()
    if request.method == "POST":
        form = RawDomainForm(request.POST)
        if form.is_valid():
            Domain.objects.create(**form.cleaned_data, insert_date=timezone.now())
            messages.add_message(request, messages.INFO, 'Target domain ' + form.cleaned_data['domain_name'] + ' added successfully')
            return http.HttpResponseRedirect(reverse('add_target_form'))
    context = {"add_target_li": "active", "target_data_active": "true", 'form': form}
    return render(request, 'target/add.html', context)

def list_target(request):
    domains = Domain.objects
    context = {'list_target_li': 'active', 'target_data_active': 'true', 'domains': domains}
    return render(request, 'target/list.html', context)

from django.shortcuts import render, get_object_or_404
from django import http
from .models import Domain
from startScan.models import ScanHistory
from django.contrib import messages
from .forms import RawTargetForm, UpdateTargetForm
from django.utils import timezone
from django.urls import reverse

def index(request):
    # TODO bring default target page
    return render(request, 'target/index.html')

def add_target_form(request):
    form = RawTargetForm()
    if request.method == "POST":
        form = RawTargetForm(request.POST)
        if form.is_valid():
            Domain.objects.create(**form.cleaned_data, insert_date=timezone.now())
            messages.add_message(request, messages.INFO, 'Target domain ' + form.cleaned_data['domain_name'] + ' added successfully')
            return http.HttpResponseRedirect(reverse('list_target'))
    context = {"add_target_li": "active", "target_data_active": "true", 'form': form}
    return render(request, 'target/add.html', context)

def list_target(request):
    domains = Domain.objects
    context = {'list_target_li': 'active', 'target_data_active': 'true', 'domains': domains}
    return render(request, 'target/list.html', context)

def delete_domain(request, id):
    obj = get_object_or_404(Domain, id=id)
    if request.method == "POST":
        obj.delete()
        responseData = {'status': 'true'}
        messages.add_message(request, messages.INFO, 'Domain successfully deleted!')
    else:
        responseData = {'status': 'false'}
        messages.add_message(request, messages.INFO, 'Oops! Domain could not be deleted!')
    return http.JsonResponse(responseData)

def update_target_form(request, id):
    domain = get_object_or_404(Domain, id=id)
    form = UpdateTargetForm()
    if request.method == "POST":
        form = UpdateTargetForm(request.POST, instance=domain)
        if form.is_valid():
            form.save()
            messages.add_message(request, messages.INFO, 'Domain edited successfully')
            return http.HttpResponseRedirect(reverse('list_target'))
    else:
        form.set_value(domain.domain_name, domain.domain_description)
    context = {'list_target_li': 'active', 'target_data_active': 'true', "domain":domain, "form":form}
    return render(request, 'target/update.html', context)

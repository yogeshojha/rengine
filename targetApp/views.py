import validators
import csv
import io
import os

from django import http
from django.shortcuts import render, get_object_or_404
from .models import Domain
from startScan.models import ScanHistory
from django.contrib import messages
from targetApp.forms import AddTargetForm, UpdateTargetForm
from django.utils import timezone
from django.urls import reverse
from django.conf import settings


def index(request):
    # TODO bring default target page
    return render(request, 'target/index.html')


def add_target_form(request):
    form = AddTargetForm(request.POST or None)
    if request.method == "POST":
        if form.is_valid():
            Domain.objects.create(
                **form.cleaned_data,
                insert_date=timezone.now())
            messages.add_message(
                request,
                messages.INFO,
                'Target domain ' +
                form.cleaned_data['domain_name'] +
                ' added successfully')
            return http.HttpResponseRedirect(reverse('list_target'))
    context = {
        "add_target_li": "active",
        "target_data_active": "true",
        'form': form}
    return render(request, 'target/add.html', context)


def import_targets(request):
    context = {}
    context['import_target_li'] = 'active'
    context['target_data_active'] = 'true'
    if request.method == 'POST':
        if 'txtFile' in request.FILES:
            txt_file = request.FILES['txtFile']
            if txt_file.content_type == 'text/plain':
                target_count = 0
                txt_content = txt_file.read().decode('UTF-8')
                io_string = io.StringIO(txt_content)
                for target in io_string:
                    if validators.domain(target):
                        Domain.objects.create(
                            domain_name=target.rstrip("\n"), insert_date=timezone.now())
                        target_count += 1
                if target_count:
                    messages.add_message(request, messages.SUCCESS, str(
                        target_count) + ' targets added successfully!')
                    return http.HttpResponseRedirect(reverse('list_target'))
                else:
                    messages.add_message(
                        request,
                        messages.ERROR,
                        'Oops! File format was invalid, could not import any targets.')
            else:
                messages.add_message(
                    request, messages.ERROR, 'Invalid File type!')
        elif 'csvFile' in request.FILES:
            csv_file = request.FILES['csvFile']
            if csv_file.content_type == 'text/csv':
                target_count = 0
                csv_content = csv_file.read().decode('UTF-8')
                io_string = io.StringIO(csv_content)
                for column in csv.reader(io_string, delimiter=','):
                    if validators.domain(column[0]):
                        Domain.objects.create(
                            domain_name=column[0],
                            domain_description=column[1],
                            insert_date=timezone.now())
                        target_count += 1
                if target_count:
                    messages.add_message(request, messages.SUCCESS, str(
                        target_count) + ' targets added successfully!')
                    return http.HttpResponseRedirect(reverse('list_target'))
                else:
                    messages.add_message(
                        request,
                        messages.ERROR,
                        'Oops! File format was invalid, could not import any targets.')
            else:
                messages.add_message(
                    request, messages.ERROR, 'Invalid File type!')
    return render(request, 'target/import.html', context)


def list_target(request):
    domains = Domain.objects.all().order_by('-insert_date')
    context = {
        'list_target_li': 'active',
        'target_data_active': 'true',
        'domains': domains}
    return render(request, 'target/list.html', context)


def delete_target(request, id):
    obj = get_object_or_404(Domain, id=id)
    if request.method == "POST":
        os.system(
            'rm -rf ' +
            settings.TOOL_LOCATION +
            'scan_results/' +
            obj.domain_name + '*')
        obj.delete()
        responseData = {'status': 'true'}
        messages.add_message(
            request,
            messages.INFO,
            'Domain successfully deleted!')
    else:
        responseData = {'status': 'false'}
        messages.add_message(
            request,
            messages.INFO,
            'Oops! Domain could not be deleted!')
    return http.JsonResponse(responseData)


def delete_targets(request):
    context = {}
    if request.method == "POST":
        list_of_domains = []
        for key, value in request.POST.items():
            if key != "style-2_length" and key != "csrfmiddlewaretoken":
                Domain.objects.filter(id=value).delete()
        messages.add_message(
            request,
            messages.INFO,
            'Targets deleted!')
    return http.HttpResponseRedirect(reverse('list_target'))


def update_target_form(request, id):
    domain = get_object_or_404(Domain, id=id)
    form = UpdateTargetForm()
    if request.method == "POST":
        form = UpdateTargetForm(request.POST, instance=domain)
        if form.is_valid():
            form.save()
            messages.add_message(
                request,
                messages.INFO,
                'Domain edited successfully')
            return http.HttpResponseRedirect(reverse('list_target'))
    else:
        form.set_value(domain.domain_name, domain.domain_description)
    context = {
        'list_target_li': 'active',
        'target_data_active': 'true',
        "domain": domain,
        "form": form}
    return render(request, 'target/update.html', context)

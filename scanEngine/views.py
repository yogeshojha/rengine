from django.shortcuts import render, get_object_or_404
from scanEngine.models import EngineType, Wordlist
from scanEngine.forms import AddEngineForm, UpdateEngineForm, AddWordlistForm
from django.contrib import messages
from django import http
from django.urls import reverse
import io
import re


def index(request):
    engine_type = EngineType.objects.all().order_by('id')
    context = {
            'scan_engine_nav_active': 'true',
            'engine_type': engine_type, }
    return render(request, 'scanEngine/index.html', context)


def add_engine(request):
    form = AddEngineForm()
    if request.method == "POST":
        form = AddEngineForm(request.POST)
        if form.is_valid():
            form.save()
            messages.add_message(
                                request,
                                messages.INFO,
                                'Scan Engine Added successfully')
            return http.HttpResponseRedirect(reverse('scan_engine_index'))
    context = {
            'scan_engine_nav_active':
            'true', 'form': form}
    return render(request, 'scanEngine/add_engine.html', context)


def delete_engine(request, id):
    obj = get_object_or_404(EngineType, id=id)
    if request.method == "POST":
        obj.delete()
        responseData = {'status': 'true'}
        messages.add_message(
                            request,
                            messages.INFO,
                            'Engine successfully deleted!')
    else:
        responseData = {'status': 'false'}
        messages.add_message(
                            request,
                            messages.INFO,
                            'Oops! Engine could not be deleted!')
    return http.JsonResponse(responseData)


def update_engine(request, id):
    engine = get_object_or_404(EngineType, id=id)
    form = UpdateEngineForm()
    if request.method == "POST":
        form = UpdateEngineForm(request.POST, instance=engine)
        if form.is_valid():
            form.save()
            messages.add_message(
                                request,
                                messages.INFO,
                                'Engine edited successfully')
            return http.HttpResponseRedirect(reverse('scan_engine_index'))
    else:
        form.set_value(engine)
    context = {
            'scan_engine_nav_active':
            'true', 'form': form}
    return render(request, 'scanEngine/update_engine.html', context)


def wordlist_list(request):
    wordlists = Wordlist.objects.all().order_by('id')
    context = {
            'wordlist_nav_active':
            'true', 'wordlists': wordlists}
    return render(request, 'scanEngine/wordlist/index.html', context)


def add_wordlist(request):
    context = {'wordlist_nav_active': 'true'}
    form = AddWordlistForm(request.POST or None, request.FILES or None)
    if request.method == "POST":
        if form.is_valid() and 'upload_file' in request.FILES:
            txt_file = request.FILES['upload_file']
            if txt_file.content_type == 'text/plain':
                wordlist_content = txt_file.read().decode('UTF-8')
                wordlist_path = '/app/tools/wordlist/'
                wordlist_file = open(
                                    wordlist_path +
                                    form.cleaned_data['short_name'] + '.txt',
                                    'w')
                wordlist_file.write(wordlist_content)
                Wordlist.objects.create(
                                        name=form.cleaned_data['name'],
                                        short_name=form.cleaned_data['short_name'],
                                        count=wordlist_content.count('\n'))
                messages.add_message(
                                    request,
                                    messages.INFO,
                                    'Wordlist ' + form.cleaned_data['name'] +
                                    ' added successfully')
                return http.HttpResponseRedirect(reverse('wordlist_list'))
    context['form'] = form
    return render(request, 'scanEngine/wordlist/add.html', context)


def delete_wordlist(request, id):
    obj = get_object_or_404(Wordlist, id=id)
    if request.method == "POST":
        obj.delete()
        responseData = {'status': 'true'}
        messages.add_message(
                            request,
                            messages.INFO,
                            'Wordlist successfully deleted!')
    else:
        responseData = {'status': 'false'}
        messages.add_message(
                            request,
                            messages.INFO,
                            'Oops! Wordlist could not be deleted!')
    return http.JsonResponse(responseData)

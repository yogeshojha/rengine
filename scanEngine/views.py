from django.shortcuts import render, get_object_or_404
from scanEngine.models import EngineType
from scanEngine.forms import AddEngineForm
from django.contrib import messages
from django import http
from django.urls import reverse

def index(request):
    engine_type = EngineType.objects.all().order_by('id')
    context = {'scan_engine_nav_active': 'true',
            'engine_type': engine_type,
            }
    return render(request, 'scanEngine/index.html', context)

def add_engine(request):
    form = AddEngineForm()
    if request.method == "POST":
        form = AddEngineForm(request.POST)
        if form.is_valid():
            form.save()
            messages.add_message(request, messages.INFO, 'Scan Engine Added successfully')
            return http.HttpResponseRedirect(reverse('scan_engine_index'))
    context = {'scan_engine_nav_active': 'true',
                'form': form}
    return render(request, 'scanEngine/add_engine.html', context)


def delete_engine(request, id):
    obj = get_object_or_404(EngineType, id=id)
    if request.method == "POST":
        obj.delete()
        responseData = {'status': 'true'}
        messages.add_message(request, messages.INFO, 'Engine successfully deleted!')
    else:
        responseData = {'status': 'false'}
        messages.add_message(request, messages.INFO, 'Oops! Engine could not be deleted!')
    return http.JsonResponse(responseData)

def update_engine(request, id):
    engine = get_object_or_404(EngineType, id=id)
    form = AddEngineForm()
    if request.method == "POST":
        form = UpdateTargetForm(request.POST, instance=engine)
        if form.is_valid():
            form.save()
            messages.add_message(request, messages.INFO, 'Engine edited successfully')
            return http.HttpResponseRedirect(reverse('scan_engine_index'))
    else:
        form.set_value(engine)
    context = {'scan_engine_nav_active': 'true','form': form}
    return render(request, 'target/update.html', context)

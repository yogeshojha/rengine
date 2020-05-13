from django.shortcuts import render
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

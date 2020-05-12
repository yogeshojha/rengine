from django.shortcuts import render
from scanEngine.models import EngineType
from scanEngine.forms import AddEngineForm

def index(request):
    engine_type = EngineType.objects.all().order_by('id')
    context = {'scan_engine_nav_active': 'true',
            'engine_type': engine_type,
            }
    return render(request, 'scanEngine/index.html', context)

def add_engine(request):
    form = AddEngineForm()
    context = {'scan_engine_nav_active': 'true',
                'form': form}
    return render(request, 'scanEngine/add_engine.html', context)

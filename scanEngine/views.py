from django.shortcuts import render
from .models import EngineType

def index(request):
    engine_type = EngineType.objects.all().order_by('id')
    context = {'scan_engine_nav_active': 'true', 'engine_type': engine_type}
    return render(request, 'scanEngine/index.html', context)

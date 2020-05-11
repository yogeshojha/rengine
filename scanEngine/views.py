from django.shortcuts import render

def index(request):
    context = {"scan_engine_nav_active": "true"}
    return render(request, 'scanEngine/index.html', context)

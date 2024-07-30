from dashboard.models import *
import requests

def projects(request):
    projects = Project.objects.all()
    try:
        slug = request.resolver_match.kwargs.get('slug')
        project = Project.objects.get(slug=slug)
    except Exception:
        project = None
    return {
        'projects': projects,
        'current_project': project
    }

def misc(request):
    externalIp = requests.get('https://checkip.amazonaws.com').text.strip()
    return {
        'external_ip': externalIp
    }
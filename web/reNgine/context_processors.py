from dashboard.models import *

def projects(request):
    projects = Project.objects.all()
    return {'projects': projects}

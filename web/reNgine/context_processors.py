from dashboard.models import *

def projects(request):
    projects = Project.objects.all()
    try:
        slug = request.resolver_match.kwargs.get('slug')
        project = Project.objects.get(slug=slug)
    except Exception as e:
        project = None
    return {
        'projects': projects,
        'current_project': project
    }

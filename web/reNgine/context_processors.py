from dashboard.models import *
from django.conf import settings


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

def version_context(request):
    return {
        'RENGINE_CURRENT_VERSION': settings.RENGINE_CURRENT_VERSION
    }

def user_preferences(request):
    if hasattr(request, 'user_preferences'):
        return {'user_preferences': request.user_preferences}
    return {}
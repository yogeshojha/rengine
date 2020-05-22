from django.shortcuts import render
from .models import NotificationHooks

def index(request):
    notification_hooks = NotificationHooks.objects
    context = {'notification_nav_active': 'true', 'all_hooks': notification_hooks}
    return render(request, 'notification/index.html', context)

from django.shortcuts import render


def index(request):
    context = {'notification_nav_active': 'true'}
    return render(request, 'notification/index.html', context)

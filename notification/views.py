from django.shortcuts import render, get_object_or_404
from .models import NotificationHooks
from django.http import HttpResponse

def index(request):
    notification_hooks = NotificationHooks.objects
    if request.method == "POST":
        print(request.body)
    context = {'notification_nav_active': 'true', 'all_hooks': notification_hooks}
    return render(request, 'notification/index.html', context)


def change_notif_status(request, id):
    if request.method == 'POST':
        notif = NotificationHooks.objects.get(id=id)
        notif.send_notif = not notif.send_notif
        notif.save()
    return HttpResponse('')

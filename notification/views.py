from django.shortcuts import render, get_object_or_404
from .models import NotificationHooks
from django.http import HttpResponse
from notification.forms import AddNotificationHooks
from django.contrib import messages
from django import http
from django.urls import reverse

def index(request):
    notification_hooks = NotificationHooks.objects
    context = {'notification_nav_active': 'true', 'all_hooks': notification_hooks}
    return render(request, 'notification/index.html', context)

def add_notification_hook(request):
    add_hook_form = AddNotificationHooks(request.POST or None)
    if add_hook_form.is_valid():
        add_hook_form.save()
        messages.add_message(request, messages.SUCCESS, 'Awesome! we will send you the scan related notifications!')
        return http.HttpResponseRedirect(reverse('notification_index'))
    context = {
        'form': add_hook_form
    }
    return render(request, 'notification/add.html', context)

def change_notif_status(request, id):
    if request.method == 'POST':
        notif = NotificationHooks.objects.get(id=id)
        notif.send_notif = not notif.send_notif
        notif.save()
    return HttpResponse('')

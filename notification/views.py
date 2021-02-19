from django.shortcuts import render, get_object_or_404
from notification.models import NotificationHooks
from django.http import HttpResponse
from notification.forms import SlackNotificationHookForm, DiscordNotificationHookForm
from django.contrib import messages
from django import http
from django.urls import reverse
import types


def index(request):
    notification_hooks = NotificationHooks.objects
    context = {
            'notification_nav_active': 'true',
            'all_hooks': notification_hooks}
    return render(request, 'notification/index.html', context)


def add_notification_hook(request):
    context = {} 
    if request.method == 'POST':
        if 'Slack' in request.POST:
            slack_form = SlackNotificationHookForm(request.POST)
            discord_form = DiscordNotificationHookForm()
            if slack_form.is_valid():
                slack_form.save()
                messages.add_message(
                                    request,
                                    messages.SUCCESS,
                                    'Awesome! We will send you' +
                                    ' scan related notifications on Slack!')
                context = {
                    'slack_form': slack_form,
                    'discord_form': discord_form
                    } 
                return http.HttpResponseRedirect(reverse('notification_index'))
        elif 'Discord' in request.POST:
            slack_form = SlackNotificationHookForm()
            discord_form = DiscordNotificationHookForm(request.POST)
            if discord_form.is_valid():
                discord_form.save()
                messages.add_message(
                                    request,
                                    messages.SUCCESS,
                                    'Awesome! We will send you' +
                                    ' scan related notifications on Discord!')
                context = {
                    'slack_form': slack_form,
                    'discord_form': discord_form
                    }
                return http.HttpResponseRedirect(reverse('notification_index'))
        
        return render(request, 'notification/add.html', context)

    elif request.method == 'GET':
        slack_form = SlackNotificationHookForm()
        discord_form = DiscordNotificationHookForm()
        context = {
            'slack_form': slack_form,
            'discord_form': discord_form
            }
        return render(request, 'notification/add.html', context)


def delete_hook(request, id):
    obj = get_object_or_404(NotificationHooks, id=id)
    if request.method == "POST":
        obj.delete()
        responseData = {'status': 'true'}
        messages.add_message(
                            request,
                            messages.INFO,
                            'Notification Hook deleted!')
    else:
        responseData = {'status': 'false'}
        messages.add_message(
                            request,
                            messages.INFO,
                            'Oops! Domain could not be deleted!')
    return http.JsonResponse(responseData)


def change_notif_status(request, id):
    if request.method == 'POST':
        notif = NotificationHooks.objects.get(id=id)
        notif.send_notif = not notif.send_notif
        notif.save()
    return HttpResponse('')

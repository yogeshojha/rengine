from django.contrib import admin
from django.urls import path, include
from . import views

urlpatterns = [
    path(
        '',
        views.index,
        name='notification_index'),
    path(
        'change/<int:id>',
        views.change_notif_status,
        name='change_notif_status'),
    path(
        'add/',
        views.add_notification_hook,
        name='add_notification_hook'),
    path(
        'delete/<int:id>',
        views.delete_hook,
        name='delete_hook'),
]

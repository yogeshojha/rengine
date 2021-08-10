from django.contrib import admin
from django.urls import path, include
from . import views


urlpatterns = [
    path(
        '',
        views.index,
        name='scan_engine_index'),
    path(
        'add/',
        views.add_engine,
        name='add_engine'),
    path(
        'delete/<int:id>',
        views.delete_engine,
        name='delete_engine_url'),
    path(
        'update/<int:id>',
        views.update_engine,
        name='update_engine'),
    path(
        'wordlist/',
        views.wordlist_list,
        name='wordlist_list'),
    path(
        'wordlist/add/',
        views.add_wordlist,
        name='add_wordlist'),
    path(
        'wordlist/delete/<int:id>',
        views.delete_wordlist,
        name='delete_wordlist'),
    path(
        'interesting/lookup/',
        views.interesting_lookup,
        name='interesting_lookup'),
    path(
        'tool_settings',
        views.tool_specific_settings,
        name='tool_settings'),
    path(
        'rengine_settings',
        views.rengine_settings,
        name='rengine_settings'),
    path(
        'notification_settings',
        views.notification_settings,
        name='notification_settings'),
    path(
        'proxy_settings',
        views.proxy_settings,
        name='proxy_settings'),
    path(
        'hackerone_settings',
        views.hackerone_settings,
        name='hackerone_settings'),
    path(
        'testHackerone/',
        views.test_hackerone,
        name='testHackerone'
    ),
]

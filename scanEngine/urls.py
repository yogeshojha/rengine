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
]

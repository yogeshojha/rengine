from django.contrib import admin
from django.urls import path, include
from . import views


urlpatterns = [
    path(
        'list_note',
        views.list_note,
        name='list_note'),
    path(
        'add_note',
        views.add_note,
        name='add_note'),
]

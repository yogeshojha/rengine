from django.contrib import admin
from django.urls import path, include
from . import views


urlpatterns = [
    path(
        'list_note',
        views.list_note,
        name='list_note'),
    path(
        'flip_todo_status',
        views.flip_todo_status,
        name='flip_todo_status'),
    path(
        'flip_important_status',
        views.flip_important_status,
        name='flip_important_status'),
    path(
        'delete_note',
        views.delete_note,
        name='delete_note'),
]

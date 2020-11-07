from django.contrib import admin
from django.urls import path, include
from . import views


urlpatterns = [
    path(
        '',
        views.index,
        name='targetIndex'),
    path(
        'add/',
        views.add_target_form,
        name='add_target_form'),
    path(
        'import/',
        views.import_targets,
        name='import_targets'),
    path(
        'update/<int:id>',
        views.update_target_form,
        name='update_target_form'),
    path(
        'list/',
        views.list_target,
        name='list_target'),
    path(
        'delete/<int:id>',
        views.delete_target,
        name='delete_target_url'),
    path(
        'delete/multiple',
        views.delete_targets,
        name='delete_multiple_targets'),
]

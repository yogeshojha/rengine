from django.contrib import admin
from django.urls import path, include
from . import views


urlpatterns = [
    path(
        '',
        views.index,
        name='targetIndex'),
    path(
        'add/target',
        views.add_target,
        name='add_target'),
    path(
        'add/organization',
        views.add_organization,
        name='add_organization'),
    path(
        'add/bulk/',
        views.add_bulk_targets,
        name='add_targets_bulk'),
    path(
        'import/',
        views.import_targets,
        name='import_targets'),
    path(
        'update/<int:id>',
        views.update_target_form,
        name='update_target_form'),
    path(
        'list/target',
        views.list_target,
        name='list_target'),
    path(
        'list/organization',
        views.list_organization,
        name='list_organization'),
    path(
        'delete/<int:id>',
        views.delete_target,
        name='delete_target_url'),
    path(
        'delete/multiple',
        views.delete_targets,
        name='delete_multiple_targets'),
    path(
        'summary/<int:id>',
        views.target_summary,
        name='target_summary'),
]

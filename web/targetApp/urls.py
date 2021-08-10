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
        'update/target/<int:id>',
        views.update_target,
        name='update_target'),
    path(
        'update/organization/<int:id>',
        views.update_organization,
        name='update_organization'),
    path(
        'list/target',
        views.list_target,
        name='list_target'),
    path(
        'list/organization',
        views.list_organization,
        name='list_organization'),
    path(
        'delete/target/<int:id>',
        views.delete_target,
        name='delete_target'),
    path(
        'delete/organization/<int:id>',
        views.delete_organization,
        name='delete_organization'),
    path(
        'delete/multiple',
        views.delete_targets,
        name='delete_multiple_targets'),
    path(
        'summary/<int:id>',
        views.target_summary,
        name='target_summary'),
]

from django.contrib import admin
from django.urls import include, path

from . import views

urlpatterns = [
    path(
        '',
        views.onboarding,
        name='onboarding'),
    path(
        '<slug:slug>/dashboard/',
        views.index,
        name='dashboardIndex'),
    path(
        '<slug:slug>/profile/',
        views.profile,
        name='profile'),
    path(
        '<slug:slug>/admin_interface/',
        views.admin_interface,
        name='admin_interface'),
    path(
        '<slug:slug>/admin_interface/update',
        views.admin_interface_update,
        name='admin_interface_update'),
    path(
        '<slug:slug>/search',
        views.search,
        name='search'),
    path(
        '404/',
        views.four_oh_four,
        name='four_oh_four'),
    path(
        '<slug:slug>/projects/',
        views.projects,
        name='list_projects'),
    path(
        'delete/project/<int:id>',
        views.delete_project,
        name='delete_project'),
    path(
        '<slug:slug>/bountyhub/list/programs',
        views.list_bountyhub_programs,
        name='list_bountyhub_programs'),
]

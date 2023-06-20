from django.contrib import admin
from django.urls import include, path

from . import views

urlpatterns = [
    path(
        '',
        views.index,
        name='dashboardIndex'),
    path(
        'profile/',
        views.profile,
        name='profile'),
    path(
        'admin_interface/',
        views.admin_interface,
        name='admin_interface'),
    path(
        'admin_interface/update',
        views.admin_interface_update,
        name='admin_interface_update'),
    path(
        'search/',
        views.search,
        name='search'),
    path(
        '404/',
        views.four_oh_four,
        name='four_oh_four'),
]

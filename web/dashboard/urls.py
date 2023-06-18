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
        'search/',
        views.search,
        name='search'),
]

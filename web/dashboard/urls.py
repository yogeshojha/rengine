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
        'search/',
        views.search,
        name='search'),
]

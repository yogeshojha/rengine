from django.contrib import admin
from django.urls import path, include
from . import views


urlpatterns = [
    path('', views.index, name='scan_engine_index'),
    path('add', views.add_engine, name='add_engine'),
]

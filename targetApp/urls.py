from django.contrib import admin
from django.urls import path, include
from . import views


urlpatterns = [
    path('', views.index, name='targetIndex'),
    path('add/', views.add_target_form, name='add_target_form'),
    path('list/', views.list_target, name='list_target'),
    path('add_target_db/', views.add_target_db, name='add_target_db'),
]

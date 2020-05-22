from django.contrib import admin
from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.index, name='notification_index'),
    path('change/<int:id>', views.change_notif_status, name='change_notif_status_api'),
]

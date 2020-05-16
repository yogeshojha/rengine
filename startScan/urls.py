from django.contrib import admin
from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.index, name="start_scan"),
    path('history/', views.scan_history, name="scan_history"),
    path('detail/<int:id>', views.detail_scan, name='detail_scan'),
]

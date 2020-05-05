from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    # path('admin/', admin.site.urls),
    path('', include('dashboard.urls'), name='dashboard'),
    path('target/', include('targetApp.urls')),
]

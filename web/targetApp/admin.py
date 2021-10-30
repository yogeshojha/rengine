from django.contrib import admin
from .models import *

admin.site.register(Domain)
admin.site.register(Organization)
admin.site.register(RegistrantInfo)
admin.site.register(WhoisDetail)
admin.site.register(DomainInfo)
admin.site.register(NameServerHistory)

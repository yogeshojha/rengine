from django.contrib import admin
from .models import *

admin.site.register(Domain)
admin.site.register(Organization)
admin.site.register(DomainInfo)
admin.site.register(AssociatedDomain)
admin.site.register(RelatedTLD)

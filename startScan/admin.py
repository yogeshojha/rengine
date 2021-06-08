from django.contrib import admin
from startScan.models import *

admin.site.register(ScanHistory)
admin.site.register(Subdomain)
admin.site.register(ScanActivity)
admin.site.register(EndPoint)
admin.site.register(Vulnerability)
admin.site.register(Port)
admin.site.register(IPAddress)
admin.site.register(Technology)

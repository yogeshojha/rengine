from django.contrib import admin
from startScan.models import ScanHistory, Subdomain, ScanActivity, \
    EndPoint, VulnerabilityScan

admin.site.register(ScanHistory)
admin.site.register(Subdomain)
admin.site.register(ScanActivity)
admin.site.register(EndPoint)
admin.site.register(VulnerabilityScan)

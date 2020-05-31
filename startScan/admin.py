from django.contrib import admin
from startScan.models import ScanHistory, ScannedHost, ScanActivity

admin.site.register(ScanHistory)
admin.site.register(ScannedHost)
admin.site.register(ScanActivity)

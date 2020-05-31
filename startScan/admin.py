from django.contrib import admin
from startScan.models import ScanHistory, ScannedHost

admin.site.register(ScanHistory)
admin.site.register(ScannedHost)

from django.contrib import admin
from startScan.models import ScanHistory, ScannedSubdomains

admin.site.register(ScanHistory)
admin.site.register(ScannedSubdomains)

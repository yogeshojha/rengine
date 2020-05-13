from django.contrib import admin
from startScan.models import ScanHistoryModel, ScannedSubdomains

admin.site.register(ScanHistoryModel)
admin.site.register(ScannedSubdomains)

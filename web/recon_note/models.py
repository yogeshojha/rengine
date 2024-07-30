from django.db import models
from startScan.models import *
from dashboard.models import Project


class TodoNote(models.Model):
    id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=1000, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    scan_history = models.ForeignKey(
        ScanHistory,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    subdomain = models.ForeignKey(
        Subdomain,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    is_done = models.BooleanField(default=False)
    is_important = models.BooleanField(default=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE)

from django.db import models
from django.utils import timezone


class Domain(models.Model):
    name = models.CharField(max_length=300, unique=True)
    description = models.TextField(blank=True, null=True)
    insert_date = models.DateTimeField()
    start_scan_date = models.DateTimeField(null=True)

    def __str__(self):
        return self.name

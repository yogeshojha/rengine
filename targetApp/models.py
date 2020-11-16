from django.db import models
from django.utils import timezone


class Domain(models.Model):
    domain_name = models.CharField(max_length=300)
    domain_description = models.TextField()
    insert_date = models.DateTimeField()
    last_scan_date = models.DateTimeField(null=True)

    def __str__(self):
        return self.domain_name

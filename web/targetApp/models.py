
from django.db import models
from django.utils import timezone
from django.apps import apps


class Organization(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=300, unique=True)
    description = models.TextField(blank=True, null=True)
    insert_date = models.DateTimeField()
    domains = models.ManyToManyField('Domain', related_name='domains')

    def __str__(self):
        return self.name

    def get_domains(self):
        return Domain.objects.filter(domains__in=Organization.objects.filter(id=self.id))


class Domain(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=300, unique=True)
    h1_team_handle = models.CharField(max_length=100, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    insert_date = models.DateTimeField()
    start_scan_date = models.DateTimeField(null=True)

    def get_organization(self):
        return Organization.objects.filter(domains__id=self.id)

    def get_recent_scan_id(self):
        ScanHistory = apps.get_model('startScan.ScanHistory')
        obj = ScanHistory.objects.filter(domain__id=self.id).order_by('-id')
        if obj:
	          return obj[0].id

    def __str__(self):
        return self.name

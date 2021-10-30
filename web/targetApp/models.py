
from django.db import models
from django.utils import timezone
from django.apps import apps


class RegistrantInfo(models.Model):
    name = models.CharField(max_length=250, null=True, blank=True)
    organization = models.CharField(max_length=250, null=True, blank=True)
    email = models.CharField(max_length=250, null=True, blank=True)
    address = models.CharField(max_length=200, null=True, blank=True)
    city = models.CharField(max_length=50, null=True, blank=True)
    state = models.CharField(max_length=20, null=True, blank=True)
    country = models.CharField(max_length=50, null=True, blank=True)
    country_iso = models.CharField(max_length=4, null=True, blank=True)
    phone_number = models.CharField(max_length=50, null=True, blank=True)
    fax = models.CharField(max_length=50, null=True, blank=True)

    def __str__(self):
        return self.name


class WhoisDetail(models.Model):
    details = models.TextField(blank=True, null=True)
    registrant = models.ForeignKey(RegistrantInfo, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return self.registrant.name


class NameServerHistory(models.Model):
    date = models.CharField(max_length=10, null=True, blank=True)
    action = models.CharField(max_length=50, null=True, blank=True)
    server = models.CharField(max_length=100, null=True, blank=True)


class NSRecord(models.Model):
    type = models.CharField(max_length=10, null=True, blank=True)
    hostname = models.CharField(max_length=50, null=True, blank=True)
    address = models.CharField(max_length=50, null=True, blank=True)
    preference = models.CharField(max_length=5, null=True, blank=True)
    ttl = models.CharField(max_length=10, null=True, blank=True)
    ns_class = models.CharField(max_length=10, null=True, blank=True)


class DomainInfo(models.Model):
    date_created = models.CharField(max_length=300, null=True, blank=True)
    domain_age = models.CharField(max_length=300, null=True, blank=True)
    ip_address = models.CharField(max_length=200, null=True, blank=True)
    geolocation = models.CharField(max_length=50, null=True, blank=True)
    geolocation_iso = models.CharField(max_length=4, null=True, blank=True)
    is_private = models.BooleanField(default=False)
    whois = models.ForeignKey(WhoisDetail, on_delete=models.CASCADE, null=True, blank=True)
    nameserver_history = models.ManyToManyField(NameServerHistory)
    nameserver_record = models.ManyToManyField(NSRecord)

    def __str__(self):
        return self.whois.registrant.name



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
    ip_address_cidr = models.CharField(max_length=100, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    insert_date = models.DateTimeField()
    start_scan_date = models.DateTimeField(null=True)
    domain_info = models.ForeignKey(DomainInfo, on_delete=models.CASCADE, null=True, blank=True)

    def get_organization(self):
        return Organization.objects.filter(domains__id=self.id)

    def get_recent_scan_id(self):
        ScanHistory = apps.get_model('startScan.ScanHistory')
        obj = ScanHistory.objects.filter(domain__id=self.id).order_by('-id')
        if obj:
	          return obj[0].id

    def __str__(self):
        return self.name

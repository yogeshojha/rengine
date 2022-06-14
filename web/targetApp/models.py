
from django.db import models
from django.utils import timezone
from django.apps import apps
from django.contrib.postgres.fields import ArrayField


class AssociatedDomain(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=250, null=True, blank=True)
    # target_id = models.ForeignKey(Domain, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return self.name


class RelatedTLD(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=250, null=True, blank=True)

    def __str__(self):
        return self.name


class NameServers(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=500, null=True, blank=True)


class RegistrarCommonModel(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=500, null=True, blank=True)
    organization = models.CharField(max_length=500, null=True, blank=True)
    address = models.CharField(max_length=700, null=True, blank=True)
    city = models.CharField(max_length=300, null=True, blank=True)
    state = models.CharField(max_length=100, null=True, blank=True)
    zip_code = models.CharField(max_length=50, null=True, blank=True)
    country = models.CharField(max_length=50, null=True, blank=True)
    email = models.CharField(max_length=500, null=True, blank=True)
    phone = models.CharField(max_length=100, null=True, blank=True)
    fax = models.CharField(max_length=100, null=True, blank=True)


class DomainRegistrant(models.Model):
    id = models.AutoField(primary_key=True)
    registrant = models.ManyToManyField(RegistrarCommonModel, blank=True)


class DomainAdmin(models.Model):
    id = models.AutoField(primary_key=True)
    registrant = models.ManyToManyField(RegistrarCommonModel, blank=True)


class DomainTechnicalContact(models.Model):
    id = models.AutoField(primary_key=True)
    registrant = models.ManyToManyField(RegistrarCommonModel, blank=True)


class DomainAbuse(models.Model):
    id = models.AutoField(primary_key=True)
    email = models.CharField(max_length=500, null=True, blank=True)
    telephone = models.CharField(max_length=100, null=True, blank=True)


class DomainInfo(models.Model):
    id = models.AutoField(primary_key=True)
    whois_raw_text = models.CharField(max_length=10000, null=True, blank=True)
    registrant = models.ManyToManyField(DomainRegistrant, blank=True)
    admin = models.ManyToManyField(DomainAdmin, blank=True)
    tech = models.ManyToManyField(DomainTechnicalContact, blank=True)
    associated_domains = models.ManyToManyField(AssociatedDomain, blank=True)
    related_tlds = models.ManyToManyField(RelatedTLD, blank=True)

    def __str__(self):
        return self.ip_address


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

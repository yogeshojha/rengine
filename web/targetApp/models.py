
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


class DomainRegisterName(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=500)


class DomainRegisterOrganization(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=500)


class DomainAddress(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=500)


class DomainCity(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)


class DomainState(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=50)


class DomainZipCode(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=20)


class DomainCountry(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=20)


class DomainEmail(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=500)


class DomainPhone(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)


class DomainFax(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)


class DomainInfo(models.Model):
    id = models.AutoField(primary_key=True)
    raw_text = models.CharField(max_length=10000, null=True, blank=True)

    # registrant
    registrant_name = models.ManyToManyField(DomainRegisterName, blank=True)
    registrant_organization = models.ManyToManyField(DomainRegisterOrganization, blank=True)
    registrant_address = models.ManyToManyField(DomainAddress, blank=True)
    registrant_city = models.ManyToManyField(DomainCity, blank=True)
    registrant_state = models.ManyToManyField(DomainState, blank=True)
    registrant_zip_code = models.ManyToManyField(DomainZipCode, blank=True)
    registrant_country = models.ManyToManyField(DomainCountry, blank=True)
    registrant_email = models.ManyToManyField(DomainEmail, blank=True)
    registrant_phone = models.ManyToManyField(DomainPhone, blank=True)
    registrant_fax = models.ManyToManyField(DomainFax, blank=True)

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

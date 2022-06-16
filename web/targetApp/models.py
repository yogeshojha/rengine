
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

    def __str__(self):
        return self.name


class DomainRegistrar(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=500)

    def __str__(self):
        return self.name


class DomainRegisterName(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=500)

    def __str__(self):
        return self.name


class DomainRegisterOrganization(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=500)

    def __str__(self):
        return self.name


class DomainAddress(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=500)

    def __str__(self):
        return self.name


class DomainCity(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class DomainState(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name


class DomainZipCode(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=20)

    def __str__(self):
        return self.name


class DomainCountry(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=20)

    def __str__(self):
        return self.name


class DomainEmail(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=500)

    def __str__(self):
        return self.name


class DomainPhone(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class DomainFax(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class DomainWhoisStatus(models.Model):
    id = models.AutoField(primary_key=True)
    status = models.CharField(max_length=500)

    def __str__(self):
        return self.name


class DomainRegistrarID(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=500)

    def __str__(self):
        return self.name


class DomainInfo(models.Model):
    id = models.AutoField(primary_key=True)
    raw_text = models.CharField(max_length=15000, null=True, blank=True)
    dnssec = models.CharField(max_length=100, null=True, blank=True)
    registrar = models.ManyToManyField(DomainRegistrar, blank=True)
    ip_address = models.CharField(max_length=200, null=True, blank=True)

    # registrant
    registrant_name = models.ManyToManyField(DomainRegisterName, blank=True, related_name='registrant_name')
    registrant_organization = models.ManyToManyField(DomainRegisterOrganization, blank=True, related_name='registrant_organization')
    registrant_address = models.ManyToManyField(DomainAddress, blank=True, related_name='registrant_address')
    registrant_city = models.ManyToManyField(DomainCity, blank=True, related_name='registrant_city')
    registrant_state = models.ManyToManyField(DomainState, blank=True, related_name='registrant_state')
    registrant_zip_code = models.ManyToManyField(DomainZipCode, blank=True, related_name='registrant_zip_code')
    registrant_country = models.ManyToManyField(DomainCountry, blank=True, related_name='registrant_country')
    registrant_email = models.ManyToManyField(DomainEmail, blank=True, related_name='registrant_email')
    registrant_phone = models.ManyToManyField(DomainPhone, blank=True, related_name='registrant_phone')
    registrant_fax = models.ManyToManyField(DomainFax, blank=True, related_name='registrant_fax')

    # Admin
    admin_name = models.ManyToManyField(DomainRegisterName, blank=True, related_name='admin_name')
    admin_id = models.ManyToManyField(DomainRegistrarID, blank=True, related_name='admin_id')
    admin_organization = models.ManyToManyField(DomainRegisterOrganization, blank=True, related_name='admin_organization')
    admin_address = models.ManyToManyField(DomainAddress, blank=True, related_name='admin_address')
    admin_city = models.ManyToManyField(DomainCity, blank=True, related_name='admin_city')
    admin_state = models.ManyToManyField(DomainState, blank=True, related_name='admin_state')
    admin_zip_code = models.ManyToManyField(DomainZipCode, blank=True, related_name='admin_zip_code')
    admin_country = models.ManyToManyField(DomainCountry, blank=True, related_name='admin_country')
    admin_email = models.ManyToManyField(DomainEmail, blank=True, related_name='admin_email')
    admin_phone = models.ManyToManyField(DomainPhone, blank=True, related_name='admin_phone')
    admin_fax = models.ManyToManyField(DomainFax, blank=True, related_name='admin_fax')

    # Tech
    tech_name = models.ManyToManyField(DomainRegisterName, blank=True, related_name='tech_name')
    tech_id = models.ManyToManyField(DomainRegistrarID, blank=True, related_name='tech_id')
    tech_organization = models.ManyToManyField(DomainRegisterOrganization, blank=True, related_name='tech_organization')
    tech_address = models.ManyToManyField(DomainAddress, blank=True, related_name='tech_address')
    tech_city = models.ManyToManyField(DomainCity, blank=True, related_name='tech_city')
    tech_state = models.ManyToManyField(DomainState, blank=True, related_name='tech_state')
    tech_zip_code = models.ManyToManyField(DomainZipCode, blank=True, related_name='tech_zip_code')
    tech_country = models.ManyToManyField(DomainCountry, blank=True, related_name='tech_country')
    tech_email = models.ManyToManyField(DomainEmail, blank=True, related_name='tech_email')
    tech_phone = models.ManyToManyField(DomainPhone, blank=True, related_name='tech_phone')
    tech_fax = models.ManyToManyField(DomainFax, blank=True, related_name='tech_fax')

    # status
    status = models.ManyToManyField(DomainWhoisStatus, blank=True)

    associated_domains = models.ManyToManyField(AssociatedDomain, blank=True)
    related_tlds = models.ManyToManyField(RelatedTLD, blank=True)

    def __str__(self):
        return self.id


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

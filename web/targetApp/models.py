
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
        return self.status


class DomainRegistrarID(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=500)

    def __str__(self):
        return self.name


class DomainInfo(models.Model):
    id = models.AutoField(primary_key=True)
    raw_text = models.CharField(max_length=15000, null=True, blank=True)
    dnssec = models.CharField(max_length=100, null=True, blank=True)
    registrar = models.ForeignKey(DomainRegistrar, blank=True, on_delete=models.CASCADE, null=True)
    ip_address = models.CharField(max_length=200, null=True, blank=True)
    created = models.DateTimeField(null=True, blank=True)
    expires = models.DateTimeField(null=True, blank=True)
    updated = models.DateTimeField(null=True, blank=True)

    # registrant
    registrant_name = models.ForeignKey(DomainRegisterName, blank=True, on_delete=models.CASCADE, related_name='registrant_name', null=True)
    registrant_organization = models.ForeignKey(DomainRegisterOrganization, blank=True, on_delete=models.CASCADE, related_name='registrant_organization', null=True)
    registrant_address = models.ForeignKey(DomainAddress, blank=True, on_delete=models.CASCADE, related_name='registrant_address', null=True)
    registrant_city = models.ForeignKey(DomainCity, blank=True, on_delete=models.CASCADE, related_name='registrant_city', null=True)
    registrant_state = models.ForeignKey(DomainState, blank=True, on_delete=models.CASCADE, related_name='registrant_state', null=True)
    registrant_zip_code = models.ForeignKey(DomainZipCode, blank=True, on_delete=models.CASCADE, related_name='registrant_zip_code', null=True)
    registrant_country = models.ForeignKey(DomainCountry, blank=True, on_delete=models.CASCADE, related_name='registrant_country', null=True)
    registrant_email = models.ForeignKey(DomainEmail, blank=True, on_delete=models.CASCADE, related_name='registrant_email', null=True)
    registrant_phone = models.ForeignKey(DomainPhone, blank=True, on_delete=models.CASCADE, related_name='registrant_phone', null=True)
    registrant_fax = models.ForeignKey(DomainFax, blank=True, on_delete=models.CASCADE, related_name='registrant_fax', null=True)

    # Admin
    admin_name = models.ForeignKey(DomainRegisterName, blank=True, on_delete=models.CASCADE, related_name='admin_name', null=True)
    admin_id = models.ForeignKey(DomainRegistrarID, blank=True, on_delete=models.CASCADE, related_name='admin_id', null=True)
    admin_organization = models.ForeignKey(DomainRegisterOrganization, blank=True, on_delete=models.CASCADE, related_name='admin_organization', null=True)
    admin_address = models.ForeignKey(DomainAddress, blank=True, on_delete=models.CASCADE, related_name='admin_address', null=True)
    admin_city = models.ForeignKey(DomainCity, blank=True, on_delete=models.CASCADE, related_name='admin_city', null=True)
    admin_state = models.ForeignKey(DomainState, blank=True, on_delete=models.CASCADE, related_name='admin_state', null=True)
    admin_zip_code = models.ForeignKey(DomainZipCode, blank=True, on_delete=models.CASCADE, related_name='admin_zip_code', null=True)
    admin_country = models.ForeignKey(DomainCountry, blank=True, on_delete=models.CASCADE, related_name='admin_country', null=True)
    admin_email = models.ForeignKey(DomainEmail, blank=True, on_delete=models.CASCADE, related_name='admin_email', null=True)
    admin_phone = models.ForeignKey(DomainPhone, blank=True, on_delete=models.CASCADE, related_name='admin_phone', null=True)
    admin_fax = models.ForeignKey(DomainFax, blank=True, on_delete=models.CASCADE, related_name='admin_fax', null=True)

    # Tech
    tech_name = models.ForeignKey(DomainRegisterName, blank=True, on_delete=models.CASCADE, related_name='tech_name', null=True)
    tech_id = models.ForeignKey(DomainRegistrarID, blank=True, on_delete=models.CASCADE, related_name='tech_id', null=True)
    tech_organization = models.ForeignKey(DomainRegisterOrganization, blank=True, on_delete=models.CASCADE, related_name='tech_organization', null=True)
    tech_address = models.ForeignKey(DomainAddress, blank=True, on_delete=models.CASCADE, related_name='tech_address', null=True)
    tech_city = models.ForeignKey(DomainCity, blank=True, on_delete=models.CASCADE, related_name='tech_city', null=True)
    tech_state = models.ForeignKey(DomainState, blank=True, on_delete=models.CASCADE, related_name='tech_state', null=True)
    tech_zip_code = models.ForeignKey(DomainZipCode, blank=True, on_delete=models.CASCADE, related_name='tech_zip_code', null=True)
    tech_country = models.ForeignKey(DomainCountry, blank=True, on_delete=models.CASCADE, related_name='tech_country', null=True)
    tech_email = models.ForeignKey(DomainEmail, blank=True, on_delete=models.CASCADE, related_name='tech_email', null=True)
    tech_phone = models.ForeignKey(DomainPhone, blank=True, on_delete=models.CASCADE, related_name='tech_phone', null=True)
    tech_fax = models.ForeignKey(DomainFax, blank=True, on_delete=models.CASCADE, related_name='tech_fax', null=True)

    # status
    status = models.ManyToManyField(DomainWhoisStatus, blank=True)
    name_servers = models.ManyToManyField(NameServers, blank=True)

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
        return str(self.name)

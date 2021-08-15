import datetime

from django.db import models
from django.db.models import JSONField
from django.core.serializers import serialize
from django.http import JsonResponse
from django.utils import timezone
from django.apps import apps

from targetApp.models import Domain
from scanEngine.models import EngineType


class ScanHistory(models.Model):
    id = models.AutoField(primary_key=True)
    start_scan_date = models.DateTimeField()
    scan_status = models.IntegerField()
    results_dir = models.CharField(max_length=100, blank=True)
    domain = models.ForeignKey(Domain, on_delete=models.CASCADE)
    scan_type = models.ForeignKey(EngineType, on_delete=models.CASCADE)
    celery_id = models.CharField(max_length=100, blank=True)
    subdomain_discovery = models.BooleanField(null=True, default=False)
    dir_file_search = models.BooleanField(null=True, default=False)
    port_scan = models.BooleanField(null=True, default=False)
    fetch_url = models.BooleanField(null=True, default=False)
    vulnerability_scan = models.BooleanField(null=True, default=False)
    osint = models.BooleanField(null=True, default=False)
    screenshot = models.BooleanField(null=True, default=True)
    stop_scan_date = models.DateTimeField(null=True)
    used_gf_patterns = models.CharField(max_length=500, null=True, blank=True)

    # osint is directly linked to scan history and not subdomains
    emails = models.ManyToManyField('Email', related_name='emails')
    employees = models.ManyToManyField('Employee', related_name='employees')
    dorks = models.ManyToManyField('Dork', related_name='dorks')

    def __str__(self):
        # debug purpose remove scan type and id in prod
        return self.domain.name

    def get_subdomain_count(self):
        return Subdomain.objects.filter(scan_history__id=self.id).count()

    def get_subdomain_change_count(self):
        last_scan = ScanHistory.objects.filter(id=self.id).filter(
            scan_type__subdomain_discovery=True).order_by('-start_scan_date')

        scanned_host_q1 = Subdomain.objects.filter(
            target_domain__id=self.domain.id).exclude(
                scan_history__id=last_scan[0].id).values('name')

        scanned_host_q2 = Subdomain.objects.filter(
            scan_history__id=last_scan[0].id).values('name')

        new_subdomains = scanned_host_q2.difference(scanned_host_q1).count()
        removed_subdomains = scanned_host_q1.difference(scanned_host_q2).count()

        return [new_subdomains, removed_subdomains]


    def get_endpoint_count(self):
        return EndPoint.objects.filter(scan_history__id=self.id).count()

    def get_vulnerability_count(self):
        return Vulnerability.objects.filter(
            scan_history__id=self.id).count()

    def get_info_vulnerability_count(self):
        return Vulnerability.objects.filter(
            scan_history__id=self.id).filter(
            severity=0).count()

    def get_low_vulnerability_count(self):
        return Vulnerability.objects.filter(
            scan_history__id=self.id).filter(
            severity=1).count()

    def get_medium_vulnerability_count(self):
        return Vulnerability.objects.filter(
            scan_history__id=self.id).filter(
            severity=2).count()

    def get_high_vulnerability_count(self):
        return Vulnerability.objects.filter(
            scan_history__id=self.id).filter(
            severity=3).count()

    def get_critical_vulnerability_count(self):
        return Vulnerability.objects.filter(
            scan_history__id=self.id).filter(
            severity=4).count()

    def get_completed_time(self):
        return self.stop_scan_date - self.start_scan_date

    def get_completed_time_in_sec(self):
        return (self.stop_scan_date - self.start_scan_date).seconds

    def get_elapsed_time(self):
        duration = timezone.now() - self.start_scan_date
        days, seconds = duration.days, duration.seconds
        hours = days * 24 + seconds // 3600
        minutes = (seconds % 3600) // 60
        seconds = seconds % 60
        if not hours and not minutes:
            return '{} seconds'.format(seconds)
        elif not hours:
            return '{} minutes'.format(minutes)
        elif not minutes:
            return '{} hours'.format(hours)
        return '{} hours {} minutes'.format(hours, minutes)


class Subdomain(models.Model):
    id = models.AutoField(primary_key=True)
    scan_history = models.ForeignKey(ScanHistory, on_delete=models.CASCADE)
    target_domain = models.ForeignKey(
        Domain, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=1000)
    is_imported_subdomain = models.BooleanField(default=False)
    is_important = models.BooleanField(default=False, null=True, blank=True)
    http_url = models.CharField(max_length=1000, null=True, blank=True)
    screenshot_path = models.CharField(max_length=1000, null=True, blank=True)
    http_header_path = models.CharField(max_length=1000, null=True, blank=True)
    directory_json = JSONField(null=True, blank=True)
    checked = models.BooleanField(default=False, blank=True, null=True)
    discovered_date = models.DateTimeField(blank=True, null=True)
    cname = models.CharField(max_length=1500, blank=True, null=True)
    is_cdn = models.BooleanField(default=False, blank=True, null=True)
    http_status = models.IntegerField(default=0)
    content_type = models.CharField(max_length=100, null=True, blank=True)
    response_time = models.FloatField(null=True, blank=True)
    webserver = models.CharField(max_length=1000, blank=True, null=True)
    content_length = models.IntegerField(default=0, blank=True, null=True)
    page_title = models.CharField(max_length=1000, blank=True, null=True)
    technologies = models.ManyToManyField('Technology', related_name='technologies')
    ip_addresses = models.ManyToManyField('IPAddress', related_name='ip_addresses')

    def __str__(self):
        return str(self.name)

    @property
    def get_endpoint_count(self):
        return EndPoint.objects.filter(
            scan_history=self.scan_history).filter(
            subdomain__name=self.name).count()

    @property
    def get_info_count(self):
        return Vulnerability.objects.filter(
            scan_history=self.scan_history).filter(
            subdomain__name=self.name).filter(severity=0).count()

    @property
    def get_low_count(self):
        return Vulnerability.objects.filter(
            scan_history=self.scan_history).filter(
            subdomain__name=self.name).filter(severity=1).count()

    @property
    def get_medium_count(self):
        return Vulnerability.objects.filter(
            scan_history=self.scan_history).filter(
            subdomain__name=self.name).filter(severity=2).count()

    @property
    def get_high_count(self):
        return Vulnerability.objects.filter(
            scan_history=self.scan_history).filter(
            subdomain__name=self.name).filter(severity=3).count()

    @property
    def get_critical_count(self):
        return Vulnerability.objects.filter(
            scan_history=self.scan_history).filter(
            subdomain__name=self.name).filter(severity=4).count()

    @property
    def get_total_vulnerability_count(self):
        return Vulnerability.objects.filter(
            scan_history=self.scan_history).filter(
            subdomain__name=self.name).count()

    @property
    def get_todos(self):
        TodoNote = apps.get_model('recon_note', 'TodoNote')
        notes = TodoNote.objects.filter(scan_history__id=self.scan_history.id).filter(subdomain__id=self.id)
        return notes.values()


class EndPoint(models.Model):
    id = models.AutoField(primary_key=True)
    scan_history = models.ForeignKey(ScanHistory, on_delete=models.CASCADE)
    target_domain = models.ForeignKey(
        Domain, on_delete=models.CASCADE, null=True, blank=True)
    subdomain = models.ForeignKey(
        Subdomain,
        on_delete=models.CASCADE,
        null=True,
        blank=True)
    http_url = models.CharField(max_length=5000)
    content_length = models.IntegerField(default=0, null=True, blank=True)
    page_title = models.CharField(max_length=1000, null=True, blank=True)
    http_status = models.IntegerField(default=0, null=True, blank=True)
    content_type = models.CharField(max_length=100, null=True, blank=True)
    discovered_date = models.DateTimeField(blank=True, null=True)
    response_time = models.FloatField(null=True, blank=True)
    webserver = models.CharField(max_length=1000, blank=True, null=True)
    is_default = models.BooleanField(null=True, blank=True, default=False)
    matched_gf_patterns = models.CharField(max_length=2000, null=True, blank=True)
    technologies = models.ManyToManyField('Technology', related_name='technology')

    def __str__(self):
        return self.http_url


class Vulnerability(models.Model):
    id = models.AutoField(primary_key=True)
    scan_history = models.ForeignKey(ScanHistory, on_delete=models.CASCADE)
    subdomain = models.ForeignKey(
        Subdomain,
        on_delete=models.CASCADE,
        null=True,
        blank=True)
    endpoint = models.ForeignKey(
        EndPoint,
        on_delete=models.CASCADE,
        blank=True,
        null=True)
    target_domain = models.ForeignKey(
        Domain, on_delete=models.CASCADE, null=True, blank=True)
    template_used = models.CharField(max_length=100)
    name = models.CharField(max_length=400)
    severity = models.IntegerField()
    description = models.CharField(max_length=10000, null=True, blank=True)
    extracted_results = models.CharField(
        max_length=3000, null=True, blank=True)
    reference = models.CharField(max_length=3000, null=True, blank=True)
    tags = models.CharField(max_length=1000, null=True, blank=True)
    http_url = models.CharField(max_length=8000, null=True)
    matcher_name = models.CharField(max_length=400, null=True, blank=True)
    discovered_date = models.DateTimeField(null=True)
    open_status = models.BooleanField(null=True, blank=True, default=True)
    hackerone_report_id = models.CharField(max_length=50, null=True, blank=True)

    def __str__(self):
        return self.name

    def get_severity(self):
        return self.severity


class ScanActivity(models.Model):
    id = models.AutoField(primary_key=True)
    scan_of = models.ForeignKey(ScanHistory, on_delete=models.CASCADE)
    title = models.CharField(max_length=1000)
    time = models.DateTimeField()
    status = models.IntegerField()

    def __str__(self):
        return str(self.title)

class Technology(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return str(self.name)


class IpAddress(models.Model):
    id = models.AutoField(primary_key=True)
    address = models.CharField(max_length=100, blank=True, null=True)
    is_cdn = models.BooleanField(default=False)
    ports = models.ManyToManyField('Port', related_name='ports')

    def __str__(self):
        return str(self.address)


class Port(models.Model):
    id = models.AutoField(primary_key=True)
    number = models.IntegerField(default=0)
    service_name = models.CharField(max_length=100, blank=True, null=True)
    description = models.CharField(max_length=1000, blank=True, null=True)
    is_uncommon = models.BooleanField(default=False)

    def __str__(self):
        return str(self.service_name)


class MetaFinderDocument(models.Model):
    id = models.AutoField(primary_key=True)
    scan_history = models.ForeignKey(ScanHistory, on_delete=models.CASCADE)
    target_domain = models.ForeignKey(
        Domain, on_delete=models.CASCADE, null=True, blank=True)
    subdomain = models.ForeignKey(
        Subdomain,
        on_delete=models.CASCADE,
        null=True,
        blank=True)
    doc_name = models.CharField(max_length=1000, null=True, blank=True)
    url = models.CharField(max_length=5000, null=True, blank=True)
    title = models.CharField(max_length=1000, null=True, blank=True)
    author = models.CharField(max_length=1000, null=True, blank=True)
    producer = models.CharField(max_length=1000, null=True, blank=True)
    creator = models.CharField(max_length=1000, null=True, blank=True)
    os = models.CharField(max_length=1000, null=True, blank=True)
    http_status = models.IntegerField(default=0, null=True, blank=True)
    creation_date = models.CharField(max_length=1000, blank=True, null=True)
    modified_date = models.CharField(max_length=1000, blank=True, null=True)


class Email(models.Model):
    id = models.AutoField(primary_key=True)
    address = models.CharField(max_length=200, blank=True, null=True)
    password = models.CharField(max_length=200, blank=True, null=True)

class Employee(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=1000, null=True, blank=True)
    designation = models.CharField(max_length=1000, null=True, blank=True)


class Dork(models.Model):
    id = models.AutoField(primary_key=True)
    type = models.CharField(max_length=500, null=True, blank=True)
    description = models.CharField(max_length=1500, null=True, blank=True)
    url = models.CharField(max_length=1500, null=True, blank=True)

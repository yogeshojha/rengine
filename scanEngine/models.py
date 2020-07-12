from django.db import models

SCAN_TYPES = ('subdomain_discovery',
                'dir_file_search',
                'subdomain_takeover',
                'port_scan')

class EngineType(models.Model):
    scan_type_name = models.CharField(max_length=200)
    subdomain_discovery = models.BooleanField(default=True)
    dir_file_search = models.BooleanField()
    subdomain_takeover = models.BooleanField()
    port_scan = models.BooleanField()
    fetch_url = models.BooleanField()
    default_engine = models.BooleanField(null=True, default=False)

    def __str__(self):
        return self.scan_type_name

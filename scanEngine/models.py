from django.db import models

SCAN_TYPES = ('subdomain_discovery',
                'dir_file_search',
                'subdomain_takeover',
                'param_discovery',
                'port_scan')

class EngineType(models.Model):
    scan_type_name = models.CharField(max_length=200)
    subdomain_discovery = models.BooleanField(default=False)
    dir_file_search = models.BooleanField(default=False)
    subdomain_takeover = models.BooleanField(default=False)
    param_discovery = models.BooleanField(default=False)
    port_scan = models.BooleanField(default=False)

    def __str__(self):
        return self.scan_type_name

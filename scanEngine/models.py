from django.db import models

SCAN_TYPES = ('subdomain_discovery',
                'dir_file_search',
                'subdomain_takeover',
                'param_discovery',
                'port_scan')

class EngineType(models.Model):
    scan_type_name = models.CharField(max_length=200)
    subdomain_discovery = models.BooleanField(default=True)
    dir_file_search = models.BooleanField()
    subdomain_takeover = models.BooleanField()
    param_discovery = models.BooleanField()
    port_scan = models.BooleanField()

    def __str__(self):
        return self.scan_type_name

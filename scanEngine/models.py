from django.db import models


class EngineType(models.Model):
    engine_name = models.CharField(max_length=200)
    subdomain_discovery = models.BooleanField()
    dir_file_search = models.BooleanField()
    port_scan = models.BooleanField()
    fetch_url = models.BooleanField()
    vulnerability_scan = models.BooleanField(null=True, default=False)
    yaml_configuration = models.TextField()
    default_engine = models.BooleanField(null=True, default=False)

    def __str__(self):
        return self.engine_name

    def get_number_of_steps(self):
        engine_list = [
            self.subdomain_discovery,
            self.dir_file_search,
            self.port_scan,
            self.fetch_url,
            self.vulnerability_scan]
        return sum(bool(item) for item in engine_list)


class Wordlist(models.Model):
    name = models.CharField(max_length=200)
    short_name = models.CharField(max_length=50, unique=True)
    count = models.IntegerField(default=0)

    def __str__(self):
        return self.name


class Configuration(models.Model):
    name = models.CharField(max_length=200)
    short_name = models.CharField(max_length=50, unique=True)
    content = models.TextField()

    def __str__(self):
        return self.name

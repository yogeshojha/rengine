from django.db import models
from django.utils import timezone

# Create your models here.
class Domain(models.Model):
    domain_name = models.CharField(max_length=300)
    domain_description = models.TextField()
    insert_date = models.DateTimeField()

    def save_domain(self):
        self.insert_date = timezone.now()
        self.save()

    def __str__(self):
        return self.domain_name

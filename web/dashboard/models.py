from django.db import models


class SearchHistory(models.Model):
    query = models.CharField(max_length=1000)

    def __str__(self):
        return self.query


class Project(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=500)
    slug = models.SlugField(unique=True)

    def __str__(self):
        return self.slug

# Generated by Django 3.2.23 on 2024-09-02 01:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0008_chaosapikey'),
    ]

    operations = [
        migrations.CreateModel(
            name='HackerOneAPIKey',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('username', models.CharField(max_length=500)),
                ('key', models.CharField(max_length=500)),
            ],
        ),
    ]
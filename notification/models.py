from django.db import models


class NotificationHooks(models.Model):
    hook_name = models.CharField(max_length=200)
    hook_url = models.CharField(max_length=500)
    send_notif = models.BooleanField()

    def __str__(self):
        return self.hook_name

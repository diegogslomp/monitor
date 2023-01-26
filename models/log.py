from django.db import models
from .status import Status
from django.utils import timezone


class HostLog(models.Model):
    """Host Logs showed in host detail view"""

    host = models.ForeignKey("monitor.Host", on_delete=models.CASCADE)
    status = models.IntegerField(choices=Status.STATUS_CHOICES, default=Status.DEFAULT)
    status_change = models.DateTimeField()
    status_info = models.CharField(max_length=200, blank=True, default="")

    def __str__(self):
        return self.host.name


class PortLog(models.Model):
    """Port Logs showed in host detail view"""

    port = models.ForeignKey("monitor.Port", on_delete=models.CASCADE, null=True)
    host = models.ForeignKey("monitor.Host", on_delete=models.CASCADE, null=True)
    counter_status = models.IntegerField(
        choices=Status.STATUS_CHOICES, default=Status.DEFAULT
    )
    counter_last_change = models.DateTimeField(
        "last status change", default=timezone.now
    )
    error_counter = models.IntegerField(default=0)

    def __str__(self):
        return self.port.number

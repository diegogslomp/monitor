from django.db import models
from .status import Status
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


class Port(models.Model):
    """Ports used to check status using telnet"""

    host = models.ForeignKey("monitor.Host", on_delete=models.CASCADE)
    number = models.CharField(max_length=20)
    is_monitored = models.BooleanField(default=False)
    counter_status = models.IntegerField(
        choices=Status.STATUS_CHOICES, default=Status.DEFAULT
    )
    counter_last_change = models.DateTimeField(
        "last status change", default=timezone.now
    )
    error_counter = models.BigIntegerField(default=0)

    def __str__(self):
        return self.number

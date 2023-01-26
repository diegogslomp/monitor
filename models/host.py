from django.db import models
from django.utils import timezone
from .status import Status
from .port import Port


class Host(models.Model):
    name = models.CharField(max_length=200)
    description = models.CharField(max_length=200, blank=True)
    ipv4 = models.GenericIPAddressField(protocol="IPv4")
    last_check = models.DateTimeField("last check", default=timezone.now)
    last_status_change = models.DateTimeField(
        "last status change", default=timezone.now
    )
    status_info = models.CharField(max_length=200, blank=True, default="")
    network = models.GenericIPAddressField(protocol="IPv4", null=True, blank=True)
    circuit = models.IntegerField(null=True, blank=True)
    retries = models.IntegerField(default=0)
    max_retries = models.IntegerField(default=1)
    local = models.CharField(max_length=200, null=True, blank=True)
    switch_manager = models.IntegerField(null=True, blank=True, default=0)
    status = models.IntegerField(choices=Status.STATUS_CHOICES, default=Status.DEFAULT)

    def __str__(self):
        return self.name

    @property
    def ports(self):
        return Port.objects.filter(host=self)

    @property
    def monitored_ports(self):
        return Port.objects.filter(host=self, is_monitored=True)

from django.core.management.base import BaseCommand
from monitor.models import Host
from monitor.models import Status
from monitor.tasks import telnet
import logging
import sys


class Command(BaseCommand):
    args = ""
    logger = logging.getLogger(__name__)
    help = "Show gateways from all hosts"

    def handle(self, *args, **options):
        self.logger.info("Show gateways started")
        for host in Host.objects.all():
            if host.status == Status.SUCCESS:
                try:
                    gateway = str(telnet.telnet_gateway(host))
                    sys.stdout.write(f"{host.ipv4:15} - {gateway:15} - {host.name}\n")
                except Exception as e:
                    self.logger.warning(f"Error reading {host} gateway")
                    self.logger.debug(e)

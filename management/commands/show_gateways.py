from django.core.management.base import BaseCommand
from monitor.models import Host, Telnet, Status
import logging
import sys


class Command(BaseCommand):
    args = ""
    logger = logging.getLogger(__name__)
    help = "Show gateways from all hosts"

    def main(self):

        for host in Host.objects.all():
            if host.status == Status.SUCCESS:
                gateway = str(Telnet.telnet_gateway(host))
                sys.stdout.write(f"{host.ipv4:15} - {gateway:15} - {host.name}\n")

    def handle(self, *args, **options):
        self.logger.info("Show gateways started")
        self.main()

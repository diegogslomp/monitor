from django.core.management.base import BaseCommand
from monitor.models import Host
from monitor.tasks import telnet
import time
import logging


class Command(BaseCommand):
    args = ""
    logger = logging.getLogger(__name__)
    help = "Monitor Port Errors from Hosts"

    def handle(self, *args, **options):
        self.logger.info("Portcounterd started")
        while True:
            for host in Host.objects.all():
                try:
                    telnet.telnet_port_counters(host)
                    time.sleep(1)
                    telnet.telnet_switch_manager(host)
                    time.sleep(1)
                except Exception as e:
                    self.logger.warning(f"Error reading {host} counters/manager")
                    self.logger.debug(e)

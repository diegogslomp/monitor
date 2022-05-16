from django.core.management.base import BaseCommand
from monitor.models import Host
import time
import logging


class Command(BaseCommand):
    args = ''
    logger = logging.getLogger(__name__)
    help = 'Monitor Port Errors from Hosts'

    def loop(self):
        while True:
            for host in Host.objects.all():
                host.telnet_port_counters()
                time.sleep(1)

    def handle(self, *args, **options):
        self.logger.info('Portcounterd started')
        self.loop()

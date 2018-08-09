from django.core.management.base import BaseCommand
from monitor.models import Host
from monitor.config.base import WAIT_FOR_NEXT
import time
import logging


class Command(BaseCommand):
    args = ''
    logger = logging.getLogger(__name__)
    help = 'Monitor Daemon for Monitor hosts'

    def loop(self):
        while True:
            for host in Host.objects.all():
                host.check_and_update_host()
                time.sleep(WAIT_FOR_NEXT)

    def handle(self, *args, **options):
        self.logger.info('monitord started')
        self.loop()

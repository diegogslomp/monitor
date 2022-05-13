from django.core.management.base import BaseCommand
from monitor.models import Host
import logging


class Command(BaseCommand):
    args = ''
    logger = logging.getLogger(__name__)
    help = 'Monitor Daemon for Monitor hosts'

    def loop(self):
        while True:
            for host in Host.objects.all():
                host.check_and_update()

    def handle(self, *args, **options):
        self.logger.info('Monitord started')
        self.loop()

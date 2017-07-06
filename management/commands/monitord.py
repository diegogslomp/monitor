from django.core.management.base import BaseCommand
from monitor.models import Host
from monitor.config.base import WAIT_FOR_NEXT
import time


class Command(BaseCommand):
    args = ''
    help = 'Monitor Daemon for Monitor hosts'

    def loop(self):
        while True:
            for host in Host.objects.all():
                host.check_status()
                time.sleep(WAIT_FOR_NEXT)

    def handle(self, *args, **options):
        self.loop()

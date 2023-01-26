from django.core.management.base import BaseCommand
from monitor.models import Host
from monitor.tasks.host import check_and_update
import logging


class Command(BaseCommand):
    args = ""
    logger = logging.getLogger(__name__)
    help = "Monitor Daemon for Monitor hosts"

    def loop(self):
        while True:
            for host in Host.objects.all():
                check_and_update(host)

    def handle(self, *args, **options):
        self.logger.info("Monitord started")
        self.loop()

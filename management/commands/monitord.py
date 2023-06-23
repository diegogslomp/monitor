from django.core.management.base import BaseCommand
from monitor.models import Host
from monitor.tasks.host import check_and_update
import logging


class Command(BaseCommand):
    args = ""
    logger = logging.getLogger(__name__)
    help = "Monitor Daemon for Monitor hosts"

    def handle(self, *args, **options):
        self.logger.info("Monitord started")
        while True:
            for host in Host.objects.all():
                try:
                    check_and_update(host)
                except Exception as e:
                    self.logger.warning(f"Error checking {host}")
                    self.logger.debug(e)

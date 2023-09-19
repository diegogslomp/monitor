from django.core.management.base import BaseCommand
from monitor.management.commands import worker
from monitor.tasks.host import check_and_update
from monitor.models import Host
import asyncio
import logging
import time

def task(host: Host) -> None:
    try:
        check_and_update(host)
        time.sleep(1)
    except Exception as e:
        logging.warning(f"Error checking {host}")
        logging.debug(e)


class Command(BaseCommand):
    args = ""
    help = "Monitor Daemon for Monitor hosts"

    def handle(self, *args, **options):
        logging.info("Monitord started")
        try:
            asyncio.run(worker.main(Host, task))
        except (KeyboardInterrupt, SystemExit):
            pass

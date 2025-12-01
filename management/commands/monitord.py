from django.core.management.base import BaseCommand
from monitor.management.commands import worker
from monitor.tasks.host import check_and_update
from monitor.models import Host
import logging
import time


def task(host: Host) -> None:
    try:
        check_and_update(host)
    except Exception as e:
        logging.warning(f"Error checking {host}")
        logging.debug(e)
    finally:
        time.sleep(1)


class Command(BaseCommand):
    args = ""
    help = "Monitor Daemon for Monitor hosts"

    def handle(self, *args, **options):
        logging.info("Monitord started")
        try:
            worker.run(model=Host, task=task)
        except (KeyboardInterrupt, SystemExit):
            pass

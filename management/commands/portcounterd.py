from django.core.management.base import BaseCommand
from monitor.models import Host, Status
from monitor.tasks import telnet
from monitor.management.commands import worker
import asyncio
import logging
import time

def task(host: Host) -> None:
    try:
        if host.status is not Status.SUCCESS:
            return
        telnet.telnet_port_counters(host)
        time.sleep(1)
        telnet.telnet_switch_manager(host)
        time.sleep(1)
    except Exception as e:
        logging.warning(f"Error checking {host} port counters/manager")
        logging.debug(e)


class Command(BaseCommand):
    args = ""
    help = "Monitor Daemon for Monitor hosts"

    def handle(self, *args, **options):
        logging.info("Portcounterd started")
        asyncio.run(worker.main(Host, task))

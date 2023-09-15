from django.core.management.base import BaseCommand
from monitor.models import Host, Status
from monitor.tasks import telnet
from monitor.management.commands import worker
import asyncio
import logging


async def task(host: Host) -> None:
    try:
        if host.status == Status.SUCCESS:
            telnet.telnet_port_counters(host)
            await asyncio.sleep(1)
            telnet.telnet_switch_manager(host)
            await asyncio.sleep(1)
    except Exception as e:
        logging.warning(f"Error checking {host} port counters/manager")
        logging.debug(e)
    finally:
        logging.debug(f"Finished {host}")


class Command(BaseCommand):
    args = ""
    help = "Monitor Daemon for Monitor hosts"

    def handle(self, *args, **options):
        logging.info("Portcounterd started")
        asyncio.run(worker.main(Host, task))

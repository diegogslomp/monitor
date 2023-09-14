from django.core.management.base import BaseCommand
from monitor.models import Host, Status
from monitor.tasks import telnet

from asyncio import Queue
from time import sleep
import asyncio
import logging


def task(host: Host):
    logging.debug(f"Working on {host}")
    try:
        if host.status == Status.SUCCESS:
            telnet.telnet_port_counters(host)
            sleep(1)
            telnet.telnet_switch_manager(host)
            sleep(1)
    except Exception as e:
        logging.warning(f"Error checking {host} port counters/manager")
        logging.debug(e)
    finally:
        logging.debug(f"Finished {host}")


async def worker(q: Queue) -> None:
    while True:
        item = await q.get()
        task(item)
        q.task_done()


async def main() -> None:
    q = Queue()

    asyncio.create_task(worker(q))

    while True:
        for host in Host.objects.all():
            q.put_nowait(host)

        # Block until all tasks are done.
        await q.join()
        logging.debug("All work completed")


class Command(BaseCommand):
    args = ""
    help = "Monitor Daemon for Monitor hosts"

    def handle(self, *args, **options):
        logging.info("Portcounterd started")
        asyncio.run(main())

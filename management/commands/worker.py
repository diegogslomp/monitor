from django.db.models import Model
from asyncio import Queue
import asyncio
import logging
import time
import os


async def worker(name: str, q: Queue, task) -> None:
    while True:
        item = await q.get()
        logging.debug(f"{name} working on {item}")

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, task, item)

        q.task_done()


async def main(model: Model, task) -> None:
    q = Queue()
    workers = int(os.getenv("WORKERS", 2))

    while True:
        for item in model.objects.all():
            await q.put(item)

        for i in range(workers):
            asyncio.create_task(worker(f"Worker-{i}", q, task))

        started_at = time.monotonic()
        await q.join()
        completed_at = time.monotonic() - started_at
        logging.debug(f"Loop completed in {completed_at:.2f} seconds")

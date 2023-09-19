from django.db.models import Model
from asyncio import Queue
import asyncio
import inspect
import logging
import os


async def handle_queue_forever(q: Queue, model: Model) -> None:
    while True:
        for item in model.objects.all():
            q.put_nowait(item)
        await q.join()


async def do_work(q: Queue, task: callable) -> None:
    while True:
        item = await q.get()
        if inspect.iscoroutinefunction(task):
            await task(item)
        else:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, task, item)
        q.task_done()


async def main(model: Model, task: callable) -> None:
    workers = []
    num_of_workers = int(os.getenv("WORKERS", 3))
    try:
        q = Queue()
        for _ in range(num_of_workers):
            workers.append(asyncio.create_task(do_work(q, task)))
        await handle_queue_forever(q, model)
    finally:
        if not workers:
            return
        for worker in workers:
            worker.cancel()
        await asyncio.gather(*workers, return_exceptions=True)
        logging.debug(f"workers dismissed")

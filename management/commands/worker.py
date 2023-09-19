from django.db.models import Model
from asyncio import Queue
import asyncio
import inspect
import logging
import os


async def handle_queue_forever(queue: Queue, model: Model) -> None:
    while True:
        for item in model.objects.all():
            queue.put_nowait(item)
        await queue.join()


async def do_work(queue: Queue, task: callable) -> None:
    while True:
        item = await queue.get()
        if inspect.iscoroutinefunction(task):
            await task(item)
        else:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, task, item)
        queue.task_done()


async def main(model: Model, task: callable) -> None:
    workers = []
    queue = Queue()
    num_of_workers = int(os.getenv("WORKERS", 3))

    for _ in range(num_of_workers):
        workers.append(asyncio.create_task(do_work(queue, task)))

    try:
        await handle_queue_forever(queue, model)
    finally:
        if workers:
            [worker.cancel() for worker in workers]
            await asyncio.gather(*workers, return_exceptions=True)
            logging.debug(f"workers dismissed")

from django.db.models import Model
from asyncio import Queue
import asyncio
import inspect
import logging
import os


async def queue_feeder(queue: Queue, model: Model) -> None:
    while True:
        for item in model.objects.all():
            queue.put_nowait(item)
        await queue.join()


async def run_work(queue: Queue, task: callable) -> None:
    while True:
        item = await queue.get()
        # Run async or sync task
        if inspect.iscoroutinefunction(task):
            await task(item)
        else:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, task, item)
        queue.task_done()


async def run_workers(model: Model, task: callable) -> None:
    queue = Queue()
    num_of_workers = int(os.getenv("WORKERS", 3))
    workers = []
    for _ in range(num_of_workers):
        workers.append(asyncio.create_task(run_work(queue=queue, task=task)))
    try:
        await queue_feeder(queue=queue, model=model)
    finally:
        # Shutdown workers
        if workers:
            [worker.cancel() for worker in workers]
            await asyncio.gather(*workers, return_exceptions=True)
            logging.debug(f"Workers dismissed")

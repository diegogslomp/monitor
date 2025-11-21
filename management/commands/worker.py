from django.db.models import Model
from asyncio import Queue
import asyncio
import inspect
import logging
import os

queue = Queue()


async def queue_feeder(model: Model) -> None:
    global queue
    while True:
        for item in model.objects.all():
            queue.put_nowait(item)
        await queue.join()


async def run_task_for_each_queue_item(task: callable) -> None:
    global queue
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
    workers = []
    num_of_workers = int(os.getenv("WORKERS", 3))

    for _ in range(num_of_workers):
        workers.append(asyncio.create_task(run_task_for_each_queue_item(task)))

    try:
        await queue_feeder(model)
    finally:
        # Shutdown workers
        if workers:
            [worker.cancel() for worker in workers]
            await asyncio.gather(*workers, return_exceptions=True)
            logging.debug(f"workers dismissed")


def main(model: Model, task: callable):
    try:
        asyncio.run(run_workers(model=model, task=task))
    except (KeyboardInterrupt, SystemExit):
        pass

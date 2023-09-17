from django.db.models import Model
from asyncio import Queue
import asyncio
import inspect
import os


async def handle_queue_forever(q: Queue, model: Model) -> None:
    while True:
        for item in model.objects.all():
            q.put_nowait(item)
        await q.join()


async def worker(q: Queue, task: callable) -> None:
    while True:
        item = await q.get()
        if inspect.iscoroutinefunction(task):
            await task(item)
        else:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, task, item)
        q.task_done()


async def main(model: Model, task: callable) -> None:
    q = Queue()

    workers = int(os.getenv("WORKERS", 3))
    for _ in range(workers):
        asyncio.create_task(worker(q, task))

    await handle_queue_forever(q, model)

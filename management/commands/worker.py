from django.db.models import Model
from asyncio import Queue, TaskGroup
import asyncio
import inspect


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


async def run_workers(model: Model, task: callable, num_of_workers=3) -> None:
    queue = Queue()
    async with TaskGroup as workers:
        for _ in range(num_of_workers):
            workers.create_task(run_work(queue=queue, task=task))
        await queue_feeder(queue=queue, model=model)

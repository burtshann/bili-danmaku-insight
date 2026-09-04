import threading
from concurrent.futures import ThreadPoolExecutor

from django.conf import settings

_executor = None
_executor_lock = threading.Lock()


def get_executor():
    global _executor
    if _executor is None:
        with _executor_lock:
            if _executor is None:
                _executor = ThreadPoolExecutor(
                    max_workers=settings.TASK_MAX_WORKERS,
                    thread_name_prefix="bili-task",
                )
    return _executor


def submit_task(task_id):
    mode = settings.TASK_EXECUTION_MODE
    if mode == "celery":
        from .tasks import execute_task_celery

        execute_task_celery.delay(str(task_id))
        return
    if mode == "inline":
        from .tasks import execute_task

        execute_task(str(task_id))
        return
    if mode != "thread":
        raise ValueError(f"Unsupported TASK_EXECUTION_MODE: {mode}")

    from .tasks import execute_task

    get_executor().submit(execute_task, str(task_id))

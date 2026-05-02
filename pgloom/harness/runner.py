from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError

from pgloom.approvals import request_approval
from pgloom.harness.registry import HandlerRegistry
from pgloom.states import TaskState
from pgloom.tasks import claim_next, retry_or_fail_task, transition_task


def run_once(
    *,
    slot: str,
    worker_id: str,
    registry: HandlerRegistry,
    database_url: str | None = None,
    lease_seconds: int = 300,
    handler_timeout_seconds: float | None = None,
) -> dict[str, object]:
    task = claim_next(
        slot=slot, worker_id=worker_id, lease_seconds=lease_seconds, database_url=database_url
    )
    if not task:
        return {"claimed": False}
    transition_task(task["id"], TaskState.RUNNING, database_url=database_url)
    try:
        handler = registry.get(task["task_type"])
        if handler_timeout_seconds is None:
            result = handler.handle(task)
        else:
            executor = ThreadPoolExecutor(max_workers=1)
            future = executor.submit(handler.handle, task)
            try:
                result = future.result(timeout=handler_timeout_seconds)
            finally:
                executor.shutdown(wait=False, cancel_futures=True)
    except TimeoutError:
        retry_or_fail_task(task["id"], reason="handler timed out", database_url=database_url)
        return {"claimed": True, "task_id": task["id"], "status": "timeout"}
    except Exception as exc:
        retry_or_fail_task(task["id"], reason=str(exc), database_url=database_url)
        return {"claimed": True, "task_id": task["id"], "status": "retry"}

    if result.status == "done":
        transition_task(task["id"], TaskState.DONE, result=result.result, database_url=database_url)
    elif result.status == "blocked":
        transition_task(
            task["id"],
            TaskState.BLOCKED,
            blocker_code=result.blocker_code or "handler_blocked",
            blocker_reason=result.blocker_reason or result.message,
            database_url=database_url,
        )
    elif result.status == "approval":
        request_approval(
            workflow_id=task["workflow_id"],
            task_id=task["id"],
            domain=task["domain"],
            prompt=result.message or "Approval requested",
            database_url=database_url,
        )
        transition_task(task["id"], TaskState.AWAITING_APPROVAL, database_url=database_url)
    else:
        retry_or_fail_task(
            task["id"],
            reason=result.message or "handler requested retry",
            database_url=database_url,
        )
    return {"claimed": True, "task_id": task["id"], "status": result.status}

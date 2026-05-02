from __future__ import annotations

from enum import StrEnum


class TaskState(StrEnum):
    QUEUED = "queued"
    LEASED = "leased"
    RUNNING = "running"
    AWAITING_REVIEW = "awaiting_review"
    AWAITING_APPROVAL = "awaiting_approval"
    AWAITING_QA = "awaiting_qa"
    BLOCKED = "blocked"
    DONE = "done"
    FAILED = "failed"
    ABANDONED = "abandoned"
    CANCELLED = "cancelled"


class WorkflowState(StrEnum):
    OPEN = "open"
    RUNNING = "running"
    AWAITING_APPROVAL = "awaiting_approval"
    BLOCKED = "blocked"
    DONE = "done"
    FAILED = "failed"
    ABANDONED = "abandoned"
    CANCELLED = "cancelled"


class ApprovalState(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


TERMINAL_TASK_STATES = {
    TaskState.DONE,
    TaskState.FAILED,
    TaskState.ABANDONED,
    TaskState.CANCELLED,
}

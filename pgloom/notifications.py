from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Protocol

import structlog
from pydantic import BaseModel, Field

from pgloom.time import utcnow


class Notification(BaseModel):
    kind: str
    workflow_id: str | None = None
    task_id: str | None = None
    approval_id: str | None = None
    message: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    occurred_at: datetime = Field(default_factory=utcnow)


class NotificationSink(Protocol):
    def emit(self, notification: Notification) -> None:
        """Emit notification to an operator channel."""


class LoggingNotificationSink:
    def __init__(self) -> None:
        self._log = structlog.get_logger(__name__)

    def emit(self, notification: Notification) -> None:
        logging.getLogger(__name__).info("%s %s", notification.kind, notification.message)
        self._log.info("notification", **notification.model_dump(mode="json"))


class NullNotificationSink:
    def emit(self, notification: Notification) -> None:
        return None


class MultiplexNotificationSink:
    """Fan-out sink. Per-sink failures are logged and do not stop later sinks."""

    def __init__(self, sinks: list[NotificationSink]) -> None:
        self._sinks = sinks

    def emit(self, notification: Notification) -> None:
        for sink in self._sinks:
            try:
                sink.emit(notification)
            except Exception:
                logging.getLogger(__name__).exception("notification sink failed")


_default_sink: NotificationSink = LoggingNotificationSink()


def get_default_sink() -> NotificationSink:
    return _default_sink


def set_default_sink(sink: NotificationSink) -> None:
    global _default_sink
    _default_sink = sink


def emit(notification: Notification) -> None:
    try:
        _default_sink.emit(notification)
    except Exception:
        logging.getLogger(__name__).exception("notification sink failed")

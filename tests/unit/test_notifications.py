from __future__ import annotations

import logging

from _pytest.logging import LogCaptureFixture

from pgloom.notifications import (
    LoggingNotificationSink,
    MultiplexNotificationSink,
    Notification,
    NullNotificationSink,
    get_default_sink,
    set_default_sink,
)


def test_logging_notification_sink_logs_kind(caplog: LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO):
        LoggingNotificationSink().emit(Notification(kind="demo.event", message="hello"))
    assert "demo.event" in caplog.text


def test_null_notification_sink_is_noop() -> None:
    NullNotificationSink().emit(Notification(kind="demo.event", message="hello"))


def test_default_sink_swap() -> None:
    sink = NullNotificationSink()
    set_default_sink(sink)
    assert get_default_sink() is sink


def test_multiplex_notification_sink_emits_to_all_children() -> None:
    class RecordingSink:
        def __init__(self) -> None:
            self.notifications: list[Notification] = []

        def emit(self, notification: Notification) -> None:
            self.notifications.append(notification)

    first = RecordingSink()
    second = RecordingSink()
    notification = Notification(kind="demo.event", message="hello")
    MultiplexNotificationSink([first, second]).emit(notification)
    assert first.notifications == [notification]
    assert second.notifications == [notification]

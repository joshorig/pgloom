from __future__ import annotations


def assert_passed(report: dict[str, object]) -> None:
    if not report.get("passed"):
        raise AssertionError(report.get("messages"))

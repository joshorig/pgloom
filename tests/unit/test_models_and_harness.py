from __future__ import annotations

import sys

from pgloom.harness.result import HandlerResult
from pgloom.harness.subprocess import run_bounded
from pgloom.models import FakeModelProvider, ModelRequest
from pgloom.models.cli import CLIModelProfile, CLIModelProvider
from pgloom.policies import RetryPolicy


def test_fake_model_provider_is_deterministic() -> None:
    provider = FakeModelProvider()
    first = provider.complete(ModelRequest(prompt="hello"))
    second = provider.complete(ModelRequest(prompt="hello"))
    assert first == second
    assert first.text.startswith("fake:")


def test_handler_result_done() -> None:
    result = HandlerResult.done({"ok": True})
    assert result.status == "done"
    assert result.result == {"ok": True}


def test_retry_policy_caps_delay() -> None:
    policy = RetryPolicy(base_delay_seconds=2, max_delay_seconds=10)
    assert policy.delay_for_attempt(8) == 10


def test_run_bounded_success() -> None:
    result = run_bounded(
        [sys.executable, "-c", "import sys; print('ok'); print('warn', file=sys.stderr)"],
        timeout_seconds=5,
    )
    assert result.exit_code == 0
    assert result.stdout.strip() == "ok"
    assert result.stderr.strip() == "warn"
    assert not result.timed_out


def test_run_bounded_timeout_kills_process() -> None:
    result = run_bounded(
        [sys.executable, "-c", "import time; time.sleep(10)"],
        timeout_seconds=0.1,
        grace_seconds=0.1,
    )
    assert result.timed_out
    assert result.exit_code != 0


def test_run_bounded_large_stderr_does_not_deadlock() -> None:
    result = run_bounded(
        [sys.executable, "-c", "import sys; sys.stderr.write('x' * (5 * 1024 * 1024))"],
        timeout_seconds=5,
    )
    assert result.exit_code == 0
    assert len(result.stderr) == 5 * 1024 * 1024


def test_cli_model_provider_records_usage(database_url: str) -> None:
    provider = CLIModelProvider(database_url=database_url)
    cli_code = (
        "import json, sys; prompt = sys.stdin.read(); "
        "print(json.dumps({'text': prompt.upper(), "
        "'usage': {'input_tokens': 7, 'output_tokens': 3}}))"
    )
    profile = CLIModelProfile(
        name="fake-cli",
        command=[
            sys.executable,
            "-c",
            cli_code,
        ],
        parse_response="json",
    )
    result = provider.invoke(profile=profile, prompt="hello")
    assert result.text == "HELLO"
    assert result.input_tokens == 7
    assert result.output_tokens == 3

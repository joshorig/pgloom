from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

from pydantic import BaseModel


class SubprocessResult(BaseModel):
    argv: list[str]
    exit_code: int
    stdout: str
    stderr: str
    duration_seconds: float
    timed_out: bool
    killed: bool


def run_bounded(
    argv: list[str],
    *,
    timeout_seconds: float,
    cwd: str | os.PathLike[str] | None = None,
    env: dict[str, str] | None = None,
    stdin: bytes | None = None,
    grace_seconds: float = 5.0,
) -> SubprocessResult:
    started = time.monotonic()
    proc_env = os.environ.copy()
    if env is not None:
        proc_env.update(env)
    process = subprocess.Popen(
        argv,
        cwd=Path(cwd) if cwd is not None else None,
        env=proc_env,
        stdin=subprocess.PIPE if stdin is not None else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    timed_out = False
    killed = False
    try:
        stdout_bytes, stderr_bytes = process.communicate(stdin, timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        timed_out = True
        process.terminate()
        try:
            stdout_bytes, stderr_bytes = process.communicate(timeout=grace_seconds)
        except subprocess.TimeoutExpired:
            killed = True
            process.kill()
            stdout_bytes, stderr_bytes = process.communicate()
    duration = time.monotonic() - started
    return SubprocessResult(
        argv=argv,
        exit_code=process.returncode if process.returncode is not None else -1,
        stdout=stdout_bytes.decode("utf-8", errors="replace"),
        stderr=stderr_bytes.decode("utf-8", errors="replace"),
        duration_seconds=duration,
        timed_out=timed_out,
        killed=killed,
    )

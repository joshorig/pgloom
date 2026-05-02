from __future__ import annotations

from typer.testing import CliRunner

from pgloom.cli import app


def test_cli_help_contains_operator_verbs() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for text in ["db", "task", "reaper", "health"]:
        assert text in result.output


def test_cli_subcommand_help() -> None:
    runner = CliRunner()
    commands = [
        ["db", "--help"],
        ["db", "check", "--help"],
        ["db", "reset", "--help"],
        ["task", "list", "--help"],
        ["task", "show", "--help"],
        ["reaper", "--help"],
        ["health", "--help"],
    ]
    for command in commands:
        result = runner.invoke(app, command)
        assert result.exit_code == 0, result.output

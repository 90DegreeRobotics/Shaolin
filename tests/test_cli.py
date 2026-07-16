"""CLI surface tests for proof/discoverability commands."""

import json

from chirox.cli import build_parser, cmd_library


def test_library_command_is_registered():
    args = build_parser().parse_args(["library", "--json"])
    assert args.func is cmd_library
    assert args.json is True


def test_library_command_lists_readable_docs(capsys):
    assert cmd_library(type("Args", (), {"json": True})()) == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    labels = {item["label"] for item in data["items"]}
    assert "the manual" in labels
    assert "the Kung Fu study guide" in labels
    assert all(item["present"] for item in data["items"])


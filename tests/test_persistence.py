"""Unit tests for src.persistence — JSONL run logging."""

import json
import tempfile
import os

from src.persistence import log_transition


class TestLogTransition:
    def test_creates_log_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "test_run.jsonl")
            os.makedirs(tmpdir, exist_ok=True)
            state_before = {"task": "test"}
            state_after = {"task": "test", "code": "print('hello')"}
            log_transition("test_run", "coder", state_before, state_after)
            assert os.path.exists(log_path)

    def test_log_contains_node_name(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "test_run.jsonl")
            os.makedirs(tmpdir, exist_ok=True)
            state_before = {"task": "test"}
            state_after = {"task": "test", "code": "print('hello')"}
            log_transition("test_run", "coder", state_before, state_after)
            with open(log_path) as f:
                entry = json.loads(f.readline())
            assert entry["node"] == "coder"

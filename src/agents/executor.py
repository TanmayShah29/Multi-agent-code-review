"""Executor — runs the Coder's script(s) in an isolated subprocess sandbox.

Supports both single-file and multi-file projects. For multi-file projects,
all files are written to the temp directory and the entry point is executed.
"""
import subprocess
import sys
import tempfile
import os
from src.config import EXECUTION_TIMEOUT
from src.state import AgentState


def _run_in_sandbox(
    files: dict[str, str], entry_point: str, timeout: int
) -> tuple[bool, str, str | None]:
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Write all files
        for rel_path, content in files.items():
            full_path = os.path.join(tmp_dir, rel_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w") as f:
                f.write(content)

        entry_path = os.path.join(tmp_dir, entry_point)

        try:
            result = subprocess.run(
                [sys.executable, entry_path],
                cwd=tmp_dir,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return False, "", f"Execution timed out after {timeout}s"

        combined_output = (result.stdout or "") + (result.stderr or "")

        if result.returncode != 0:
            return False, combined_output, combined_output or f"Exited with code {result.returncode}"

        return True, combined_output, None


def executor_node(state: AgentState) -> AgentState:
    files = state.get("files") or {"main.py": state["code"]}
    entry_point = state.get("entry_point", "main.py")
    passed, output, error = _run_in_sandbox(files, entry_point, EXECUTION_TIMEOUT)
    return {
        **state,
        "execution_passed": passed,
        "execution_output": output,
        "execution_error": error,
    }

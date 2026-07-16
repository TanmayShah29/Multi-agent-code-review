"""Docker-based sandboxed executor (Phase 9 stretch goal).

Same interface/contract as agents/executor.py, but runs the Coder's script
inside an ephemeral, network-disabled, resource-capped Docker container
instead of a bare subprocess — real process isolation instead of "just a
temp directory".

Requires Docker installed and running locally, and the `python:3.11-slim`
image available (pulled automatically on first run).
"""
import subprocess
import tempfile
import os
from src.config import EXECUTION_TIMEOUT
from src.state import AgentState

DOCKER_IMAGE = "python:3.11-slim"


def _run_in_docker(
    files: dict[str, str], entry_point: str, timeout: int
) -> tuple[bool, str, str | None]:
    with tempfile.TemporaryDirectory() as tmp_dir:
        for rel_path, content in files.items():
            full_path = os.path.join(tmp_dir, rel_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w") as f:
                f.write(content)

        entry_path = os.path.join(tmp_dir, entry_point)

        cmd = [
            "docker", "run", "--rm",
            "--network", "none",
            "--memory", "128m",
            "--cpus", "0.5",
            "--pids-limit", "64",
            "-v", f"{tmp_dir}:/sandbox:ro",
            "-w", "/sandbox",
            DOCKER_IMAGE,
            "python", entry_point,
        ]

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return False, "", f"Execution timed out after {timeout}s"
        except FileNotFoundError:
            return False, "", (
                "Docker is not installed or not on PATH. Install Docker Desktop "
                "or set SANDBOX_BACKEND=subprocess in .env to use the plain "
                "subprocess sandbox instead."
            )

        combined_output = (result.stdout or "") + (result.stderr or "")

        if result.returncode != 0:
            return False, combined_output, combined_output or f"Exited with code {result.returncode}"

        return True, combined_output, None


def executor_docker_node(state: AgentState) -> AgentState:
    files = state.get("files") or {"main.py": state["code"]}
    entry_point = state.get("entry_point", "main.py")
    passed, output, error = _run_in_docker(files, entry_point, EXECUTION_TIMEOUT)
    return {
        **state,
        "execution_passed": passed,
        "execution_output": output,
        "execution_error": error,
    }

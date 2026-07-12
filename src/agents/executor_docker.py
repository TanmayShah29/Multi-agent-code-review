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
from typing import Optional, Tuple
from src.config import EXECUTION_TIMEOUT
from src.state import AgentState

DOCKER_IMAGE = "python:3.11-slim"


def _run_in_docker(code: str, timeout: int) -> Tuple[bool, str, Optional[str]]:
    with tempfile.TemporaryDirectory() as tmp_dir:
        script_path = os.path.join(tmp_dir, "solution.py")
        with open(script_path, "w") as f:
            f.write(code)

        cmd = [
            "docker", "run", "--rm",
            "--network", "none",
            "--memory", "128m",
            "--cpus", "0.5",
            "--pids-limit", "64",
            "-v", f"{tmp_dir}:/sandbox:ro",
            "-w", "/sandbox",
            DOCKER_IMAGE,
            "python", "solution.py",
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
    passed, output, error = _run_in_docker(state["code"], EXECUTION_TIMEOUT)
    return {
        **state,
        "execution_passed": passed,
        "execution_output": output,
        "execution_error": error,
    }

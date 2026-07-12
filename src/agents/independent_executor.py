"""Independent Test Executor — runs the Tester agent's adversarial test suite
against the Coder's solution in a sandboxed subprocess, completely separate
from the Coder's own self-test block. This is what makes the Tester agent
meaningful: its tests are graded by execution, not by another LLM's opinion.

Supports multi-file projects: all files are written to the temp directory
before the test harness runs.
"""
import subprocess
import sys
import tempfile
import os
from src.config import EXECUTION_TIMEOUT
from src.state import AgentState

_DRIVER_TEMPLATE = '''
import solution

{tester_code}

if __name__ == "__main__":
    try:
        run_tests(solution)
        print("ALL INDEPENDENT TESTS PASSED")
    except AssertionError as e:
        print(f"TESTER FAILED: {{e}}")
        import sys
        sys.exit(1)
    except Exception as e:
        print(f"TESTER ERRORED: {{e}}")
        import sys
        sys.exit(1)
'''


def _run_independent_tests(
    files: dict[str, str], entry_point: str, tester_code: str, timeout: int
):
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Write all project files
        for rel_path, content in files.items():
            full_path = os.path.join(tmp_dir, rel_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w") as f:
                f.write(content)

        # For the test harness, we need a single "solution" module.
        # If multi-file, create an __init__.py-style package or import shim.
        if len(files) == 1:
            # Single file: write as solution.py
            solution_path = os.path.join(tmp_dir, "solution.py")
            with open(solution_path, "w") as f:
                f.write(next(iter(files.values())))
        else:
            # Multi-file: create a package that re-exports everything
            pkg_dir = os.path.join(tmp_dir, "solution_pkg")
            os.makedirs(pkg_dir, exist_ok=True)
            for rel_path, content in files.items():
                pkg_file = os.path.join(pkg_dir, rel_path)
                os.makedirs(os.path.dirname(pkg_file), exist_ok=True)
                with open(pkg_file, "w") as f:
                    f.write(content)

            # Create solution.py that imports from the package
            init_imports = []
            for rel_path in files:
                module = rel_path.replace("/", ".").replace(".py", "")
                if module.endswith(".__init__"):
                    module = module[:-9]
                init_imports.append(f"from solution_pkg import {module}")

            solution_path = os.path.join(tmp_dir, "solution.py")
            with open(solution_path, "w") as f:
                f.write("\n".join(init_imports) + "\n")

        driver_path = os.path.join(tmp_dir, "test_harness.py")
        with open(driver_path, "w") as f:
            f.write(_DRIVER_TEMPLATE.format(tester_code=tester_code))

        try:
            result = subprocess.run(
                [sys.executable, driver_path],
                cwd=tmp_dir,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return False, "", f"Independent tests timed out after {timeout}s"

        combined_output = (result.stdout or "") + (result.stderr or "")

        if result.returncode != 0:
            return False, combined_output, combined_output or f"Exited with code {result.returncode}"

        return True, combined_output, None


def independent_test_node(state: AgentState) -> AgentState:
    files = state.get("files") or {"main.py": state["code"]}
    entry_point = state.get("entry_point", "main.py")
    passed, output, error = _run_independent_tests(
        files, entry_point, state.get("tester_code", ""), EXECUTION_TIMEOUT
    )
    return {
        **state,
        "tester_passed": passed,
        "tester_output": output,
        "tester_error": error,
    }

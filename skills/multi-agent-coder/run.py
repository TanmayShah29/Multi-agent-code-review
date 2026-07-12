#!/usr/bin/env python3
"""Multi-Agent Coder Skill — entry point.

Usage:
    python run.py "Write a Python function that validates IPv4 addresses"
    python run.py --verbose "Build a web scraper project"
    python run.py --json "Create a REST API client"

Output modes:
    (default)   Streaming CLI with colored progress
    --json      JSON output with full state (for programmatic use)
    --quiet     Only output the final code/files
"""
import sys
import os
import json
import time

# Add parent directory to path so we can import src
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.config import MAX_ITERATIONS
from src.graph import build_graph
from src.state import AgentState
from src.persistence import new_run_id
from src.tools.github import is_github_issue_url, fetch_issue_as_task


def _make_initial_state(task: str, max_iterations: int) -> AgentState:
    return {
        "task": task,
        "plan": "",
        "plan_valid": False,
        "plan_validation_feedback": "",
        "code": "",
        "files": {},
        "entry_point": "main.py",
        "review_verdict": "",
        "review_feedback": "",
        "execution_passed": False,
        "execution_output": "",
        "execution_error": None,
        "tester_code": "",
        "tester_passed": False,
        "tester_output": "",
        "tester_error": None,
        "iteration": 0,
        "max_iterations": max_iterations,
        "done": False,
        "final_status": "",
        "total_input_tokens": 0,
        "total_output_tokens": 0,
        "total_cost": 0.0,
    }


# ANSI colors
C = {
    "planner": "\033[36m", "validator": "\033[33m", "coder": "\033[32m",
    "reviewer": "\033[35m", "executor": "\033[34m", "tester": "\033[91m",
    "independent_executor": "\033[93m", "success": "\033[92m", "give_up": "\033[91m",
}
R = "\033[0m"
B = "\033[1m"
LABELS = {
    "planner": "PLANNER", "validator": "VALIDATOR", "coder": "CODER",
    "reviewer": "REVIEWER", "executor": "EXECUTOR", "tester": "TESTER",
    "independent_executor": "IND. TESTER", "success": "DONE", "give_up": "GAVE UP",
}


def _print_update(node, state, verbose):
    if node == "planner" and state.get("plan"):
        print(f"  Plan generated ({state['plan'].count(chr(10)) + 1} lines)")
    elif node == "validator":
        if state.get("plan_valid"):
            print(f"  Plan validated ✓")
        else:
            fb = state.get("plan_validation_feedback", "")[:100]
            print(f"  Plan rejected: {fb}...")
    elif node == "coder":
        files = state.get("files", {})
        if len(files) > 1:
            print(f"  Generated {len(files)} files: {', '.join(files.keys())}")
        else:
            print(f"  Code generated ({state['code'].count(chr(10)) + 1} lines)")
    elif node == "reviewer":
        v = state.get("review_verdict", "")
        color = "\033[32m" if v == "APPROVED" else "\033[31m"
        print(f"  Verdict: {color}{v}{R}")
    elif node == "executor":
        p = state.get("execution_passed", False)
        color = "\033[32m" if p else "\033[31m"
        print(f"  Self-test: {color}{'PASSED' if p else 'FAILED'}{R}")
    elif node == "independent_executor":
        p = state.get("tester_passed", False)
        color = "\033[32m" if p else "\033[31m"
        print(f"  Independent tests: {color}{'PASSED' if p else 'FAILED'}{R}")
    elif node in ("success", "give_up"):
        print(f"  {state.get('final_status', '')}")

    if verbose and node == "executor" and state.get("execution_output"):
        for line in state["execution_output"].split("\n")[:10]:
            print(f"    {line}")
    if verbose and node == "independent_executor" and state.get("tester_output"):
        for line in state["tester_output"].split("\n")[:10]:
            print(f"    {line}")


def run_skill(task: str, mode: str = "stream", verbose: bool = False) -> dict:
    """Run the multi-agent pipeline. Returns final state dict."""
    if is_github_issue_url(task):
        print(f"Fetching GitHub issue...")
        task = fetch_issue_as_task(task)

    run_id = new_run_id()
    graph = build_graph(run_id=run_id)
    state = _make_initial_state(task, MAX_ITERATIONS)

    if mode == "stream":
        print(f"\n{'═' * 60}")
        print(f"  MULTI-AGENT CODE REVIEW")
        print(f"{'═' * 60}")
        print(f"  Task: {task[:80]}{'...' if len(task) > 80 else ''}")
        print(f"{'═' * 60}")

    final_state = None
    for step in graph.stream(state, stream_mode="updates"):
        for node_name, node_state in step.items():
            final_state = node_state
            if mode == "stream":
                ts = time.strftime("%H:%M:%S")
                color = C.get(node_name, "")
                label = LABELS.get(node_name, node_name.upper())
                print(f"\n{color}{B}[{ts}] {label}{R}")
                print(f"{color}{'─' * 50}{R}")
                _print_update(node_name, node_state, verbose)

    return final_state


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    flags = [a for a in sys.argv[1:] if a.startswith("-")]

    if not args:
        print('Usage: python run.py [--verbose|--json|--quiet] "task description"')
        sys.exit(1)

    task = " ".join(args)
    verbose = "--verbose" in flags or "-v" in flags
    mode_json = "--json" in flags
    mode_quiet = "--quiet" in flags

    mode = "json" if mode_json else ("quiet" if mode_quiet else "stream")
    final_state = run_skill(task, mode=mode, verbose=verbose)

    if mode == "json":
        # Clean state for JSON serialization
        output = {k: v for k, v in final_state.items() if k != "tester_code"}
        print(json.dumps(output, indent=2, default=str))

    elif mode == "quiet":
        files = final_state.get("files", {})
        if len(files) > 1:
            for path, content in files.items():
                print(f"# === {path} ===")
                print(content)
                print()
        else:
            print(final_state.get("code", ""))

    else:
        # Streaming mode — print final report
        print("\n" + "=" * 70)
        print("FINAL CODE" if len(final_state.get("files", {})) <= 1 else "GENERATED FILES")
        print("=" * 70)
        files = final_state.get("files", {})
        if len(files) > 1:
            for path, content in files.items():
                print(f"\n--- {path} ---")
                print(content)
        else:
            print(final_state.get("code", ""))

        print("\n" + "=" * 70)
        print("SELF-TEST OUTPUT")
        print("=" * 70)
        print(final_state.get("execution_output", ""))

        if final_state.get("tester_output"):
            print("\n" + "=" * 70)
            print("INDEPENDENT TEST OUTPUT")
            print("=" * 70)
            print(final_state["tester_output"])

        print("\n" + "=" * 70)
        print("STATUS")
        print("=" * 70)
        print(final_state.get("final_status", ""))

        if final_state.get("total_cost", 0) > 0:
            print(f"\nTokens: {final_state['total_input_tokens']} in / {final_state['total_output_tokens']} out")
            print(f"Cost: ${final_state['total_cost']:.4f}")

    sys.exit(0 if final_state.get("tester_passed") else 1)


if __name__ == "__main__":
    main()

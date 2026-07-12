"""CLI entrypoint with real-time streaming progress.

Usage:
    python -m src.main "Write a Python function that validates IPv4 addresses, with tests"
    python -m src.main "https://github.com/owner/repo/issues/123"
    python -m src.main --verbose "Build a web scraper with multiple modules"
"""
import sys
import time
from src.config import MAX_ITERATIONS
from src.graph import build_graph
from src.state import AgentState
from src.persistence import new_run_id
from src.tools.github import is_github_issue_url, fetch_issue_as_task

# ANSI colors for terminal output
_COLORS = {
    "planner": "\033[36m",      # cyan
    "validator": "\033[33m",    # yellow
    "coder": "\033[32m",        # green
    "reviewer": "\033[35m",     # magenta
    "executor": "\033[34m",     # blue
    "tester": "\033[91m",       # light red
    "independent_executor": "\033[93m",  # light yellow
    "success": "\033[92m",      # light green
    "give_up": "\033[91m",      # light red
}
_RESET = "\033[0m"
_BOLD = "\033[1m"

_AGENT_LABELS = {
    "planner": "PLANNER",
    "validator": "VALIDATOR",
    "coder": "CODER",
    "reviewer": "REVIEWER",
    "executor": "EXECUTOR",
    "tester": "TESTER",
    "independent_executor": "IND. TESTER",
    "success": "DONE",
    "give_up": "GAVE UP",
}


def _resolve_task(raw_arg: str) -> str:
    if is_github_issue_url(raw_arg):
        print(f"Detected GitHub issue URL — fetching issue body from {raw_arg} ...")
        return fetch_issue_as_task(raw_arg)
    return raw_arg


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


def _print_node_header(node_name: str, iteration: int) -> None:
    color = _COLORS.get(node_name, "")
    label = _AGENT_LABELS.get(node_name, node_name.upper())
    timestamp = time.strftime("%H:%M:%S")
    print(f"\n{color}{_BOLD}[{timestamp}] {label}{_RESET}")
    print(f"{color}{'─' * 50}{_RESET}")


def _print_streaming_update(node_name: str, state: AgentState, verbose: bool) -> None:
    """Print a summary after each node completes."""
    if node_name == "planner" and state.get("plan"):
        plan_lines = state["plan"].count("\n") + 1
        print(f"  Plan generated ({plan_lines} lines)")

    elif node_name == "validator":
        if state.get("plan_valid"):
            print(f"  Plan validated ✓")
        else:
            feedback = state.get("plan_validation_feedback", "")[:100]
            print(f"  Plan rejected: {feedback}...")

    elif node_name == "coder":
        files = state.get("files", {})
        if len(files) > 1:
            print(f"  Generated {len(files)} files: {', '.join(files.keys())}")
        else:
            code_lines = state["code"].count("\n") + 1
            print(f"  Code generated ({code_lines} lines)")

    elif node_name == "reviewer":
        verdict = state.get("review_verdict", "")
        color = "\033[32m" if verdict == "APPROVED" else "\033[31m"
        print(f"  Verdict: {color}{verdict}{_RESET}")
        if verdict == "REJECTED" and state.get("review_feedback"):
            feedback = state["review_feedback"][:150]
            print(f"  Feedback: {feedback}...")

    elif node_name == "executor":
        passed = state.get("execution_passed", False)
        color = "\033[32m" if passed else "\033[31m"
        print(f"  Self-test: {color}{'PASSED' if passed else 'FAILED'}{_RESET}")
        if verbose and state.get("execution_output"):
            for line in state["execution_output"].split("\n")[:10]:
                print(f"    {line}")

    elif node_name == "tester":
        print(f"  Test suite generated")

    elif node_name == "independent_executor":
        passed = state.get("tester_passed", False)
        color = "\033[32m" if passed else "\033[31m"
        print(f"  Independent tests: {color}{'PASSED' if passed else 'FAILED'}{_RESET}")
        if verbose and state.get("tester_output"):
            for line in state["tester_output"].split("\n")[:10]:
                print(f"    {line}")

    elif node_name == "success":
        print(f"  {state.get('final_status', '')}")

    elif node_name == "give_up":
        print(f"  {state.get('final_status', '')}")


def run_streaming(task: str, run_id: str | None = None, verbose: bool = False) -> AgentState:
    """Run the graph with real-time streaming output."""
    graph = build_graph(run_id=run_id)
    state = _make_initial_state(task, MAX_ITERATIONS)

    print(f"\n{'═' * 60}")
    print(f"  MULTI-AGENT CODE REVIEW")
    print(f"{'═' * 60}")
    print(f"  Task: {task[:80]}{'...' if len(task) > 80 else ''}")
    print(f"  Model: from config")
    print(f"{'═' * 60}")

    final_state = None
    for step in graph.stream(state, stream_mode="updates"):
        for node_name, node_state in step.items():
            final_state = node_state
            _print_node_header(node_name, node_state.get("iteration", 0))
            _print_streaming_update(node_name, node_state, verbose)

    return final_state


def run(task: str, run_id: str | None = None) -> AgentState:
    """Run the graph without streaming (blocking)."""
    graph = build_graph(run_id=run_id)
    state = _make_initial_state(task, MAX_ITERATIONS)
    return graph.invoke(state)


def _print_report(state: AgentState, run_id: str) -> None:
    print("\n" + "=" * 70)
    print("PLAN")
    print("=" * 70)
    print(state["plan"])

    files = state.get("files", {})
    if len(files) > 1:
        print("\n" + "=" * 70)
        print(f"GENERATED FILES ({len(files)} files)")
        print("=" * 70)
        for path, content in files.items():
            print(f"\n--- {path} ---")
            print(content)
    else:
        print("\n" + "=" * 70)
        print("FINAL CODE")
        print("=" * 70)
        print(state["code"])

    print("\n" + "=" * 70)
    print("SELF-TEST EXECUTION OUTPUT")
    print("=" * 70)
    print(state["execution_output"])

    if state.get("tester_output"):
        print("\n" + "=" * 70)
        print("INDEPENDENT TEST OUTPUT")
        print("=" * 70)
        print(state["tester_output"])

    print("\n" + "=" * 70)
    print("STATUS")
    print("=" * 70)
    print(state["final_status"])

    if state.get("total_cost", 0) > 0:
        print(f"\nTokens: {state['total_input_tokens']} in / {state['total_output_tokens']} out")
        print(f"Cost: ${state['total_cost']:.4f}")

    print(f"\nRun log saved to runs/{run_id}.jsonl")


def main():
    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("-")]

    if not args:
        print('Usage: python -m src.main [--verbose] "<task description or GitHub issue URL>"')
        sys.exit(1)

    task = _resolve_task(" ".join(args))
    run_id = new_run_id()
    final_state = run_streaming(task, run_id=run_id, verbose=verbose)
    _print_report(final_state, run_id)
    sys.exit(0 if final_state.get("tester_passed") else 1)


if __name__ == "__main__":
    main()

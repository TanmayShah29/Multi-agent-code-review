"""Persists each node's state transition to disk for later debugging/analysis.

Each run gets a single JSONL file under runs/, one line per node execution,
so you can replay exactly what each agent saw and produced without having to
re-run (and re-pay for) the LLM calls.
"""
import json
import os
import time
import functools

RUNS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "runs")


def new_run_id() -> str:
    return time.strftime("%Y%m%d-%H%M%S")


def log_transition(run_id: str, node_name: str, state_before: dict, state_after: dict) -> None:
    os.makedirs(RUNS_DIR, exist_ok=True)
    path = os.path.join(RUNS_DIR, f"{run_id}.jsonl")
    record = {
        "timestamp": time.time(),
        "node": node_name,
        "iteration": state_after.get("iteration"),
        "state_before": dict(state_before),
        "state_after": dict(state_after),
    }
    with open(path, "a") as f:
        f.write(json.dumps(record) + "\n")


def with_logging(node_name: str, run_id: str, fn):
    """Wrap a LangGraph node function so every invocation is appended to the
    run's JSONL log. `fn` must have the (state) -> state signature all our
    agent nodes share.
    """

    @functools.wraps(fn)
    def wrapped(state):
        state_after = fn(state)
        log_transition(run_id, node_name, state, state_after)
        return state_after

    return wrapped

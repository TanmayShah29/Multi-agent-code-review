"""Builds the LangGraph state machine wiring:

    planner -> validator -> coder -> reviewer -> executor -> tester -> independent_executor -> success

looping back to the Planner on invalid plans, and to the Coder on rejection,
self-test execution failure, or independent-test failure, up to max_iterations.

Supports streaming: call graph.stream() to get real-time updates as each
node completes.
"""
import os
from langgraph.graph import StateGraph, END
from src.state import AgentState
from src.agents.planner import planner_node
from src.agents.validator import validator_node
from src.agents.coder import coder_node
from src.agents.reviewer import reviewer_node
from src.agents.executor import executor_node
from src.agents.executor_docker import executor_docker_node
from src.agents.tester import tester_node
from src.agents.independent_executor import independent_test_node
from src.persistence import with_logging

SANDBOX_BACKEND = os.getenv("SANDBOX_BACKEND", "subprocess")  # "subprocess" | "docker"


def _after_validation(state: AgentState) -> str:
    if state["plan_valid"]:
        return "coder"
    if state["iteration"] >= state["max_iterations"]:
        return "give_up"
    return "planner"


def _after_review(state: AgentState) -> str:
    if state["review_verdict"] == "APPROVED":
        return "executor"
    if state["iteration"] >= state["max_iterations"]:
        return "give_up"
    return "coder"


def _after_execution(state: AgentState) -> str:
    if state["execution_passed"]:
        return "tester"
    if state["iteration"] >= state["max_iterations"]:
        return "give_up"
    return "coder"


def _after_independent_test(state: AgentState) -> str:
    if state["tester_passed"]:
        return "success"
    if state["iteration"] >= state["max_iterations"]:
        return "give_up"
    return "coder"


def _success_node(state: AgentState) -> AgentState:
    return {
        **state,
        "done": True,
        "final_status": (
            f"SUCCESS after {state['iteration']} iteration(s) — self-test and "
            f"independent tests both passed."
        ),
    }


def _give_up_node(state: AgentState) -> AgentState:
    if state.get("plan_valid") is False:
        reason = state.get("plan_validation_feedback", "plan validation failed")
    elif state.get("review_verdict") == "REJECTED":
        reason = state.get("review_feedback")
    elif state.get("execution_passed") is False:
        reason = state.get("execution_error")
    else:
        reason = state.get("tester_error")

    return {
        **state,
        "done": True,
        "final_status": (
            f"GAVE UP after {state['iteration']} iteration(s) "
            f"(max_iterations={state['max_iterations']}). Last issue: {reason}"
        ),
    }


def build_graph(run_id: str | None = None):
    """If run_id is given, every node invocation is appended to
    runs/<run_id>.jsonl via src.persistence for later debugging/replay.
    """
    graph = StateGraph(AgentState)

    executor_fn = executor_docker_node if SANDBOX_BACKEND == "docker" else executor_node

    nodes = {
        "planner": planner_node,
        "validator": validator_node,
        "coder": coder_node,
        "reviewer": reviewer_node,
        "executor": executor_fn,
        "tester": tester_node,
        "independent_executor": independent_test_node,
        "success": _success_node,
        "give_up": _give_up_node,
    }

    for name, fn in nodes.items():
        graph.add_node(name, with_logging(name, run_id, fn) if run_id else fn)

    graph.set_entry_point("planner")

    graph.add_edge("planner", "validator")

    graph.add_conditional_edges(
        "validator",
        _after_validation,
        {"coder": "coder", "planner": "planner", "give_up": "give_up"},
    )

    graph.add_edge("coder", "reviewer")

    graph.add_conditional_edges(
        "reviewer",
        _after_review,
        {"executor": "executor", "coder": "coder", "give_up": "give_up"},
    )

    graph.add_conditional_edges(
        "executor",
        _after_execution,
        {"tester": "tester", "coder": "coder", "give_up": "give_up"},
    )

    graph.add_edge("tester", "independent_executor")

    graph.add_conditional_edges(
        "independent_executor",
        _after_independent_test,
        {"success": "success", "coder": "coder", "give_up": "give_up"},
    )

    graph.add_edge("success", END)
    graph.add_edge("give_up", END)

    return graph.compile()

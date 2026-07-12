"""Shared state threaded through every node in the LangGraph workflow."""
from typing import TypedDict, Optional


class AgentState(TypedDict):
    # Original user request, unchanged throughout the run.
    task: str

    # Output of the Planner — a numbered implementation plan.
    plan: str

    # Validator feedback on the plan (empty if valid).
    plan_valid: bool
    plan_validation_feedback: str

    # Most recent code produced by the Coder. For single-file tasks this is
    # the entire solution; for multi-file tasks it's the entry point.
    code: str

    # Multi-file output: {relative_path: file_content}. The Coder populates
    # this for projects that need more than one file. For single-file tasks
    # this will contain just {"main.py": <code>}.
    files: dict[str, str]

    # The file the Executor should run as the entry point.
    entry_point: str

    # Reviewer's verdict: "APPROVED" or "REJECTED".
    review_verdict: str

    # Reviewer's written feedback (empty string if approved with nothing to add).
    review_feedback: str

    # Executor's output (runs the Coder's own self-test block).
    execution_passed: bool
    execution_output: str  # combined stdout/stderr
    execution_error: Optional[str]

    # Tester agent's independent adversarial test harness, and the result of
    # running it against the Coder's solution (separate from the Coder's own
    # self-test, and separate from the Reviewer's LLM judgment).
    tester_code: str
    tester_passed: bool
    tester_output: str
    tester_error: Optional[str]

    # Loop bookkeeping.
    iteration: int
    max_iterations: int

    # Set to True once the graph should stop (either success or exhausted retries).
    done: bool

    # Human-readable final status message set by the graph's terminal node.
    final_status: str

    # Cost tracking: cumulative tokens and USD cost across all LLM calls.
    total_input_tokens: int
    total_output_tokens: int
    total_cost: float

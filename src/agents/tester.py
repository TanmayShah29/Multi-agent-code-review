"""Tester Agent — writes independent, adversarial tests against the Coder's
solution, so correctness isn't graded only by the Coder's own self-test or by
the Reviewer's LLM judgment. Its tests are graded by actually running them
(see agents/independent_executor.py), not by another LLM reading them.
"""
import re
from src.llm import get_llm
from src.state import AgentState

_llm = get_llm(temperature=0.3)

SYSTEM_PROMPT = """You are the Tester in a multi-agent software engineering team.
You did NOT write the code below — a separate Coder agent did. Write independent,
adversarial tests that check the code against the plan, focusing on edge cases
the Coder may not have exercised in its own self-test (empty input, boundary
values, malformed/invalid input, large input, type edge cases, etc).

Output ONLY a single ```python fenced block defining exactly one function:

    def run_tests(module):
        ...

`module` is the imported solution module — call the functions under test via
`module.<function_name>(...)`. Use plain `assert` statements with clear messages
(e.g. `assert result == expected, f"expected {expected}, got {result}"`).
Do not redefine or reimplement the solution's logic — only call and check it.
Do not print anything yourself; the test harness that calls `run_tests` handles
reporting.
"""


def _extract_code(text: str) -> str:
    match = re.search(r"```python\s*(.*?)```", text, re.DOTALL)
    return match.group(1).strip() if match else text.strip()


def tester_node(state: AgentState) -> AgentState:
    response = _llm.invoke(
        [
            ("system", SYSTEM_PROMPT),
            (
                "user",
                f"Plan:\n{state['plan']}\n\nCode:\n```python\n{state['code']}\n```",
            ),
        ]
    )
    return {**state, "tester_code": _extract_code(response.content)}

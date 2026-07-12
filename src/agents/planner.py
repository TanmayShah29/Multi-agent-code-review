"""Planner Agent — turns a raw task description into a concrete implementation plan."""
from src.llm import get_llm
from src.state import AgentState

_llm = get_llm(temperature=0.2)

SYSTEM_PROMPT = """You are the Planner in a multi-agent software engineering team.
Given a coding task, produce a concise, numbered implementation plan for a
Python project that a Coder agent will write. Your plan should specify:

1. What the project needs to do, function by function.
2. Key edge cases to handle (list them explicitly).
3. What the self-test / `if __name__ == "__main__"` block should verify.
4. Which files to create if this is a multi-file project (with paths).

Keep it tight — a Coder agent will read this plan directly, so prefer concrete
specifics ("function `validate_ipv4(addr: str) -> bool`") over vague prose.
Do not write any code yourself — plan only.
"""


def planner_node(state: AgentState) -> AgentState:
    user_parts = [f"Task:\n{state['task']}"]

    if state.get("plan_validation_feedback"):
        user_parts.append(
            f"The Validator rejected your previous plan with this feedback:\n"
            f"{state['plan_validation_feedback']}\n\n"
            f"Please fix the issues and produce a better plan."
        )

    response = _llm.invoke(
        [
            ("system", SYSTEM_PROMPT),
            ("user", "\n\n".join(user_parts)),
        ]
    )
    return {**state, "plan": response.content}

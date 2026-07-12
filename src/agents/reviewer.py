"""Reviewer Agent — critiques the Coder's output against the plan before it's run."""
import re
from src.llm import get_llm
from src.state import AgentState

_llm = get_llm(temperature=0.0)

SYSTEM_PROMPT = """You are the Reviewer in a multi-agent software engineering team.
You will be given an implementation plan and the code a Coder agent wrote for it.

Check for:
- Correctness relative to the plan.
- Obvious bugs, unhandled edge cases, or logic errors.
- Whether the self-test block actually verifies the intended behavior.

Respond in EXACTLY this format:

VERDICT: APPROVED
or
VERDICT: REJECTED

FEEDBACK: <if REJECTED, concrete, actionable feedback for the Coder.
If APPROVED, this can be a one-line note or "None".>

Be strict but fair — reject for real bugs or missing edge cases, not style
preferences. Do not rewrite the code yourself.
"""


def reviewer_node(state: AgentState) -> AgentState:
    response = _llm.invoke(
        [
            ("system", SYSTEM_PROMPT),
            (
                "user",
                f"Plan:\n{state['plan']}\n\nCode:\n```python\n{state['code']}\n```",
            ),
        ]
    )
    text = response.content

    verdict_match = re.search(r"VERDICT:\s*(APPROVED|REJECTED)", text, re.IGNORECASE)
    feedback_match = re.search(r"FEEDBACK:\s*(.*)", text, re.DOTALL)

    verdict = verdict_match.group(1).upper() if verdict_match else "REJECTED"
    feedback = feedback_match.group(1).strip() if feedback_match else text.strip()

    return {
        **state,
        "review_verdict": verdict,
        "review_feedback": feedback,
    }

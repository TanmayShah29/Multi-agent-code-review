"""Validator Agent — checks the Planner's output is well-formed before the
Coder starts writing code. Catches vague or incomplete plans early so the
Coder doesn't waste tokens on a bad foundation.

If the plan is invalid, the Validator provides concrete feedback that gets
sent back to the Planner on the next loop iteration.
"""
import re
from src.llm import get_llm
from src.state import AgentState

_llm = get_llm(temperature=0.0)

SYSTEM_PROMPT = """You are the Validator in a multi-agent software engineering team.
Your job is to check whether an implementation plan is well-formed and complete
before the Coder starts writing code.

A good plan must:
1. Be non-empty and have clear, numbered steps.
2. Specify function signatures (name, parameters, return type).
3. List key edge cases to handle.
4. Describe what the self-test / `if __name__ == "__main__"` block should verify.
5. Be specific enough that a Coder agent can implement it without guessing.

Respond in EXACTLY this format:

VALID: YES
or
VALID: NO

FEEDBACK: <If NO, concrete, actionable feedback for the Planner on what to fix.
If YES, "None".>

Be strict — a vague plan leads to wasted iterations. Reject plans that say
things like "handle edge cases" without listing them, or that omit function
signatures.
"""


def validator_node(state: AgentState) -> AgentState:
    response = _llm.invoke(
        [
            ("system", SYSTEM_PROMPT),
            ("user", f"Task:\n{state['task']}\n\nPlan:\n{state['plan']}"),
        ]
    )
    text = response.content

    valid_match = re.search(r"VALID:\s*(YES|NO)", text, re.IGNORECASE)
    feedback_match = re.search(r"FEEDBACK:\s*(.*)", text, re.DOTALL)

    is_valid = valid_match.group(1).upper() == "YES" if valid_match else False
    feedback = feedback_match.group(1).strip() if feedback_match else text.strip()

    return {
        **state,
        "plan_valid": is_valid,
        "plan_validation_feedback": feedback if not is_valid else "",
    }

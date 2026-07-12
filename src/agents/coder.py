"""Coder Agent — writes/revises Python code to satisfy the plan.

On the first pass it only sees the plan. On retries it also sees the previous
code plus whatever feedback (review rejection or execution error) triggered
the retry, so it can make a targeted fix rather than starting from scratch.

Supports multi-file output: the Coder can produce multiple files using fenced
code blocks with `# file: <path>` headers.
"""
import re
import json
from src.llm import get_llm
from src.state import AgentState

_llm = get_llm(temperature=0.2)

SYSTEM_PROMPT = """You are the Coder in a multi-agent software engineering team.
Write complete, runnable Python code that satisfies the given plan.

## Single-file tasks
If the plan describes a single script, output ONLY a single ```python fenced
code block. No prose before or after.

## Multi-file projects
If the plan describes multiple files, output each file as a separate fenced
block, with a comment on the line BEFORE each fence specifying the path:

# file: src/main.py
```python
...
```

# file: src/utils.py
```python
...
```

## Rules for ALL tasks
- The code must be self-contained and runnable.
- Include an `if __name__ == "__main__":` block in the entry point that
  exercises the code and prints clear PASS/FAIL output, so the Executor can
  verify correctness by checking the exit code and stdout.
- Exit with a non-zero exit code (e.g. `sys.exit(1)`) if any self-test fails.
- Use standard library only, unless the plan explicitly requires otherwise.
"""


def _extract_files(text: str) -> dict[str, str]:
    """Parse multi-file output. Looks for `# file: <path>` followed by a
    fenced code block. Falls back to extracting a single code block for
    backward-compatible single-file output.
    """
    files = {}
    pattern = r"#\s*file:\s*(.+?)\n```(?:python)?\s*\n(.*?)```"
    for match in re.finditer(pattern, text, re.DOTALL):
        path = match.group(1).strip()
        code = match.group(2).strip()
        files[path] = code

    if files:
        return files

    # Fallback: single code block with no file header
    match = re.search(r"```python\s*(.*?)```", text, re.DOTALL)
    if match:
        return {"main.py": match.group(1).strip()}

    return {"main.py": text.strip()}


def coder_node(state: AgentState) -> AgentState:
    user_parts = [f"Plan:\n{state['plan']}"]

    if state.get("files"):
        file_list = "\n".join(f"  {p}" for p in state["files"])
        user_parts.append(f"Previous files:\n{file_list}")

    if state.get("review_verdict") == "REJECTED" and state.get("review_feedback"):
        user_parts.append(f"Reviewer feedback to address:\n{state['review_feedback']}")

    if state.get("execution_passed") is False and state.get("execution_error"):
        user_parts.append(
            f"The previous code failed when executed. Error/output:\n"
            f"{state['execution_error']}"
        )

    if state.get("tester_passed") is False and state.get("tester_error"):
        user_parts.append(
            f"An independent Tester agent (not you) wrote extra tests and the "
            f"code failed them. Fix the underlying bug, don't just special-case "
            f"the test:\n{state['tester_error']}"
        )

    response = _llm.invoke(
        [
            ("system", SYSTEM_PROMPT),
            ("user", "\n\n".join(user_parts)),
        ]
    )

    files = _extract_files(response.content)

    # Determine entry point: prefer "main.py", else first file
    entry_point = "main.py" if "main.py" in files else next(iter(files))

    # For backward compat, set code to the entry point's content
    code = files[entry_point]

    return {
        **state,
        "code": code,
        "files": files,
        "entry_point": entry_point,
        "iteration": state.get("iteration", 0) + 1,
    }

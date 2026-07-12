# Multi-Agent Coder Skill

A multi-agent coding pipeline that autonomously plans, codes, reviews, tests, and validates Python code.

## When to use

Use this skill when you need to:
- Generate complete, tested Python code from a task description
- Build multi-file Python projects with proper structure
- Get automated code review and adversarial testing
- Iterate on code until it passes all checks

## How to invoke

```bash
python skills/multi-agent-coder/run.py "Your task description here"
```

Or with verbose output:
```bash
python skills/multi-agent-coder/run.py --verbose "Your task description here"
```

## Pipeline

1. **Planner** — Analyzes the task and creates a numbered implementation plan
2. **Validator** — Checks the plan is well-formed before coding begins
3. **Coder** — Generates code (single file or multi-file project)
4. **Reviewer** — Reviews code against the plan, approves or rejects with feedback
5. **Executor** — Runs self-tests in a sandboxed subprocess
6. **Tester** — Writes independent adversarial tests
7. **Independent Executor** — Runs the adversarial tests in a separate sandbox

If any step fails, the pipeline loops back with feedback, up to `MAX_ITERATIONS`.

## Configuration

Set in `.env` or environment:

```
GEMINI_API_KEY=your-key          # Required
LLM_PROVIDER=google_genai        # anthropic, openai, groq, etc.
AGENT_MODEL=gemini-2.5-flash     # Model to use
MAX_ITERATIONS=4                 # Max retry loops
EXECUTION_TIMEOUT=10             # Seconds before sandbox timeout
SANDBOX_BACKEND=subprocess       # or "docker"
```

## Output

- **CLI**: Real-time streaming progress with colored output
- **Files**: Generated code written to `runs/<timestamp>/`
- **Logs**: Full JSONL trace of every agent's state at `runs/<run_id>.jsonl`

## Multi-file projects

When the task requires multiple files, the Coder outputs them with headers:

```python
# file: src/main.py
```python
...
```

# file: src/utils.py
```python
...
```

The Executor writes all files to a temp directory and runs the entry point.

## Requirements

```bash
pip install langgraph langchain-google-genai langchain-core python-dotenv requests
```

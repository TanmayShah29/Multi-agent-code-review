# Multi-Agent Code Review

A multi-agent coding pipeline built with LangGraph. Takes a natural-language task (or GitHub issue) and autonomously plans, codes, reviews, tests, and validates the output — no human in the loop.

```
Planner → Validator → Coder → Reviewer → Executor → Tester → Independent Executor
         ↑                      ↑                         │
         └── invalid plan ──────┘                         │
         └─────────────── retry on failure ───────────────┘
```

## Why this exists

Most AI code generators call an LLM once and hope for the best. This system uses a team of specialized agents that loop until the code is correct:

- **Plan before you code** — a Planner breaks the task into steps, a Validator catches bad plans early
- **Code, then review** — a Reviewer checks the Coder's output against the plan, rejects with feedback if wrong
- **Test independently** — a Tester writes adversarial tests the Coder never sees, graded by actual execution
- **Retry with context** — failures loop back with feedback, not from scratch

## Quick start

```bash
git clone https://github.com/yourname/multi-agent-code-review.git
cd multi-agent-code-review
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add your API key
```

## Usage

```bash
# Basic task
python -m src.main "Write a Python function that validates IPv4 addresses, with tests"

# Verbose — shows test output inline
python -m src.main --verbose "Build an LRU cache with O(1) get/put"

# GitHub issue as input
python -m src.main "https://github.com/owner/repo/issues/42"

# Streamlit UI
streamlit run src/ui.py
```

## How it works

### The pipeline

| Agent | Job | LLM? |
|-------|-----|------|
| **Planner** | Task → numbered implementation plan | yes |
| **Validator** | Checks plan is well-formed before coding | yes |
| **Coder** | Plan → runnable code (single or multi-file) | yes |
| **Reviewer** | Code → `APPROVED` / `REJECTED` + feedback | yes |
| **Executor** | Runs self-test in sandboxed subprocess | no |
| **Tester** | Writes independent adversarial test suite | yes |
| **Independent Executor** | Runs Tester's suite in separate sandbox | no |

The graph loops back to the Coder from any failure point (review rejection, self-test failure, independent test failure) up to `MAX_ITERATIONS`.

### Multi-file projects

When the task requires multiple files, the Coder outputs them with path headers:

```python
# file: src/models.py
class User:
    ...

# file: src/api.py
from models import User
...
```

All files are written to the sandbox and the entry point is executed.

### Streaming progress

The CLI shows real-time updates as each agent completes:

```
[14:48:07] PLANNER
  Plan generated (27 lines)

[14:48:10] VALIDATOR
  Plan validated ✓

[14:48:14] CODER
  Generated 3 files: src/models.py, src/api.py, src/main.py

[14:48:20] REVIEWER
  Verdict: APPROVED

[14:48:20] EXECUTOR
  Self-test: PASSED
```

## Bring your own AI

Every agent calls `get_llm()` instead of importing a provider SDK directly. Change three lines in `.env` to switch providers — no code changes.

| Provider | Model example | API key | Install |
|----------|--------------|---------|---------|
| Google Gemini | `gemini-2.5-flash` | `GEMINI_API_KEY` | `langchain-google-genai` |
| Anthropic | `claude-sonnet-4-6` | `ANTHROPIC_API_KEY` | `langchain-anthropic` |
| OpenAI | `gpt-5` | `OPENAI_API_KEY` | `langchain-openai` |
| Groq | `llama-3.3-70b-versatile` | `GROQ_API_KEY` | `langchain-groq` |
| Ollama | `llama3.1` (local, free) | none | `langchain-ollama` |
| + Mistral, xAI, Fireworks, Together, Cohere, Bedrock | | | |

Universal override: set `LLM_API_KEY` instead of provider-specific vars.

## Configuration

`.env` options:

```bash
LLM_PROVIDER=google_genai     # anthropic | openai | google_genai | groq | ollama | ...
AGENT_MODEL=gemini-2.5-flash  # model name for the chosen provider
GEMINI_API_KEY=your-key       # API key (or use provider-specific var)
MAX_ITERATIONS=4              # max retry loops before giving up
EXECUTION_TIMEOUT=10          # seconds before sandbox kills the script
SANDBOX_BACKEND=subprocess    # "subprocess" (default) or "docker"
```

## Project structure

```
src/
  config.py                 # env/config: provider, model, API key, iterations
  llm.py                    # get_llm(temperature) — provider-agnostic model factory
  state.py                  # AgentState TypedDict — single contract for all nodes
  graph.py                  # LangGraph wiring: nodes, conditional edges, retry logic
  main.py                   # CLI entrypoint with streaming progress
  ui.py                     # Streamlit UI with real-time updates
  persistence.py            # run_id + per-node JSONL logging to runs/
  agents/
    planner.py              # task → implementation plan
    validator.py            # checks plan is well-formed
    coder.py                # plan → code (single or multi-file)
    reviewer.py             # code → APPROVED/REJECTED + feedback
    executor.py             # subprocess sandbox
    executor_docker.py      # Docker sandbox (SANDBOX_BACKEND=docker)
    tester.py               # adversarial test suite
    independent_executor.py # runs Tester's suite in separate sandbox
  tools/
    github.py               # fetch GitHub issue body as task input
skills/
  multi-agent-coder/        # optional: use as a Claude Code / OpenCode skill
```

## Run history

Every run logs each agent's state to `runs/<run_id>.jsonl` for debugging and replay without re-paying for LLM calls.

## Docker sandbox (optional)

For real process isolation (no host filesystem access, resource limits):

```bash
# in .env
SANDBOX_BACKEND=docker
```

Requires Docker installed and running locally.

## As a skill (Claude Code / OpenCode)

This project also works as a skill for Claude Code or OpenCode:

```bash
python skills/multi-agent-coder/run.py "Your task here"          # streaming
python skills/multi-agent-coder/run.py --json "Your task here"   # JSON output
python skills/multi-agent-coder/run.py --quiet "Your task here"  # just the code
```

## License

MIT

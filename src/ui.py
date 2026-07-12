"""Streamlit UI with real-time streaming progress.

Run with:
    streamlit run src/ui.py
"""
import streamlit as st
from src.config import MAX_ITERATIONS
from src.graph import build_graph
from src.persistence import new_run_id
from src.state import AgentState
from src.tools.github import is_github_issue_url, fetch_issue_as_task

st.set_page_config(page_title="Multi-Agent Coder", layout="wide")
st.title("🤖 Multi-Agent Coding / Code Review Workflow")
st.caption("Planner → Validator → Coder → Reviewer → Executor → Tester → Independent Test Executor")

task_input = st.text_area(
    "Task (or paste a GitHub issue URL)",
    placeholder="Write a Python function that validates IPv4 addresses, with tests",
    height=100,
)
max_iters = st.number_input("Max iterations", min_value=1, max_value=10, value=MAX_ITERATIONS)
run_button = st.button("Run", type="primary")

if run_button and task_input.strip():
    task = task_input.strip()
    if is_github_issue_url(task):
        with st.spinner("Fetching GitHub issue..."):
            task = fetch_issue_as_task(task)
        st.text_area("Resolved task (from GitHub issue)", value=task, height=100, disabled=True)

    run_id = new_run_id()
    graph = build_graph(run_id=run_id)

    initial_state: AgentState = {
        "task": task,
        "plan": "",
        "plan_valid": False,
        "plan_validation_feedback": "",
        "code": "",
        "files": {},
        "entry_point": "main.py",
        "review_verdict": "",
        "review_feedback": "",
        "execution_passed": False,
        "execution_output": "",
        "execution_error": None,
        "tester_code": "",
        "tester_passed": False,
        "tester_output": "",
        "tester_error": None,
        "iteration": 0,
        "max_iterations": int(max_iters),
        "done": False,
        "final_status": "",
        "total_input_tokens": 0,
        "total_output_tokens": 0,
        "total_cost": 0.0,
    }

    # Streaming progress display
    status_container = st.container()
    progress_bar = st.progress(0)
    status_text = st.empty()

    node_order = ["planner", "validator", "coder", "reviewer", "executor", "tester", "independent_executor"]
    node_labels = {
        "planner": "📋 Planning",
        "validator": "✅ Validating Plan",
        "coder": "💻 Coding",
        "reviewer": "🔍 Reviewing",
        "executor": "⚡ Executing",
        "tester": "🧪 Writing Tests",
        "independent_executor": "🎯 Running Independent Tests",
    }

    completed_nodes = set()
    final_state = None

    for step in graph.stream(initial_state, stream_mode="updates"):
        for node_name, node_state in step.items():
            final_state = node_state
            completed_nodes.add(node_name)

            # Update progress
            if node_name in node_order:
                idx = node_order.index(node_name)
                progress = (idx + 1) / len(node_order)
                progress_bar.progress(progress)

            # Show status for each completed node
            with status_container:
                if node_name == "planner" and node_state.get("plan"):
                    with st.status("📋 Planning...", expanded=False) as status:
                        st.markdown(node_state["plan"][:500])
                        status.update(label="📋 Plan complete", state="complete")

                elif node_name == "validator":
                    if node_state.get("plan_valid"):
                        st.success("✅ Plan validated")
                    else:
                        st.warning(f"⚠️ Plan rejected: {node_state.get('plan_validation_feedback', '')[:200]}")

                elif node_name == "coder":
                    files = node_state.get("files", {})
                    with st.status("💻 Generating code...", expanded=False) as status:
                        if len(files) > 1:
                            for path, content in files.items():
                                st.caption(path)
                                st.code(content, language="python")
                        else:
                            st.code(node_state.get("code", ""), language="python")
                        status.update(label=f"💻 Code complete ({len(files)} files)", state="complete")

                elif node_name == "reviewer":
                    verdict = node_state.get("review_verdict", "")
                    if verdict == "APPROVED":
                        st.success(f"🔍 Review: {verdict}")
                    else:
                        st.error(f"🔍 Review: {verdict}")
                        if node_state.get("review_feedback"):
                            st.caption(node_state["review_feedback"][:300])

                elif node_name == "executor":
                    passed = node_state.get("execution_passed", False)
                    if passed:
                        st.success("⚡ Self-test passed")
                    else:
                        st.error("⚡ Self-test failed")
                        if node_state.get("execution_error"):
                            st.code(node_state["execution_error"][:500])

                elif node_name == "independent_executor":
                    passed = node_state.get("tester_passed", False)
                    if passed:
                        st.success("🎯 Independent tests passed")
                    else:
                        st.error("🎯 Independent tests failed")

            status_text.text(f"Completed: {node_labels.get(node_name, node_name)}")

    progress_bar.progress(1.0)

    if final_state:
        st.divider()

        # Final status
        if final_state.get("tester_passed"):
            st.success(final_state["final_status"])
        else:
            st.error(final_state["final_status"])

        # Plan
        with st.expander("📋 Plan", expanded=False):
            st.markdown(final_state.get("plan", ""))

        # Generated files
        files = final_state.get("files", {})
        if len(files) > 1:
            st.subheader(f"📁 Generated Files ({len(files)} files)")
            for path, content in files.items():
                with st.expander(path, expanded=False):
                    st.code(content, language="python")
        else:
            st.subheader("📝 Final Code")
            st.code(final_state.get("code", ""), language="python")

        # Test outputs
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("⚡ Self-Test Output")
            st.code(final_state.get("execution_output") or "(no output)")
        with col2:
            st.subheader("🎯 Independent Test Output")
            st.code(final_state.get("tester_output") or "(no output)")

        # Cost tracking
        if final_state.get("total_cost", 0) > 0:
            st.caption(f"Tokens: {final_state['total_input_tokens']} in / {final_state['total_output_tokens']} out | Cost: ${final_state['total_cost']:.4f}")

        st.caption(f"Run log saved to runs/{run_id}.jsonl")

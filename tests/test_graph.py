"""Unit tests for src.graph — routing functions."""

from src.graph import (
    _after_validation,
    _after_review,
    _after_execution,
    _after_independent_test,
)


class TestAfterValidation:
    def test_valid_plan_goes_to_coder(self):
        state = {"plan_valid": True, "iteration": 1, "max_iterations": 4}
        assert _after_validation(state) == "coder"

    def test_invalid_plan_loops_back(self):
        state = {"plan_valid": False, "iteration": 1, "max_iterations": 4}
        assert _after_validation(state) == "planner"

    def test_invalid_plan_gives_up_at_max(self):
        state = {"plan_valid": False, "iteration": 4, "max_iterations": 4}
        assert _after_validation(state) == "give_up"


class TestAfterReview:
    def test_approved_goes_to_executor(self):
        state = {"review_verdict": "APPROVED", "iteration": 1, "max_iterations": 4}
        assert _after_review(state) == "executor"

    def test_rejected_goes_to_coder(self):
        state = {"review_verdict": "REJECTED", "iteration": 1, "max_iterations": 4}
        assert _after_review(state) == "coder"

    def test_rejected_gives_up_at_max(self):
        state = {"review_verdict": "REJECTED", "iteration": 4, "max_iterations": 4}
        assert _after_review(state) == "give_up"


class TestAfterExecution:
    def test_passed_goes_to_tester(self):
        state = {"execution_passed": True, "iteration": 1, "max_iterations": 4}
        assert _after_execution(state) == "tester"

    def test_failed_loops_back(self):
        state = {"execution_passed": False, "iteration": 1, "max_iterations": 4}
        assert _after_execution(state) == "coder"

    def test_failed_gives_up_at_max(self):
        state = {"execution_passed": False, "iteration": 4, "max_iterations": 4}
        assert _after_execution(state) == "give_up"


class TestAfterIndependentTest:
    def test_all_passed_ends(self):
        state = {"tester_passed": True, "iteration": 1, "max_iterations": 4}
        assert _after_independent_test(state) == "success"

    def test_any_failed_goes_to_coder(self):
        state = {"tester_passed": False, "iteration": 1, "max_iterations": 4}
        assert _after_independent_test(state) == "coder"

    def test_failed_gives_up_at_max(self):
        state = {"tester_passed": False, "iteration": 4, "max_iterations": 4}
        assert _after_independent_test(state) == "give_up"

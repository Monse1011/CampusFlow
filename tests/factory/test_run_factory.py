"""Orchestrator state machine tests. They never call Gemini."""

import pytest

from scripts.run_factory import next_stage, parse_recommendation


@pytest.fixture
def run(tmp_path):
    return tmp_path


def state(requirements="PENDING", plan="PENDING"):
    gates = dict.fromkeys(["review", "release"], "PENDING")
    return {"human_gates": {**gates, "requirements": requirements, "plan": plan}}


def test_starts_with_intake(run):
    assert next_stage(run, state()) == "intake"


def test_planner_blocked_until_product_owner_approves(run):
    (run / "01-intake-report.md").write_text("x")
    assert next_stage(run, state()) == "await_requirements"
    assert next_stage(run, state(requirements="REJECTED")) == "await_requirements"
    assert next_stage(run, state(requirements="APPROVED")) == "plan"


def test_coder_blocked_until_tech_lead_approves(run):
    (run / "01-intake-report.md").write_text("x")
    (run / "02-plan.md").write_text("x")
    assert next_stage(run, state("APPROVED")) == "await_plan"
    assert next_stage(run, state("APPROVED", "DEFERRED")) == "await_plan"
    assert next_stage(run, state("APPROVED", "REJECTED")) == "plan"
    assert next_stage(run, state("APPROVED", "MODIFIED")) == "coder"


def test_recommendation_parsing_fails_safe():
    assert parse_recommendation("...\nRECOMMENDATION: PROCEED") == "PROCEED"
    assert parse_recommendation("no recommendation line") == "HUMAN_CLARIFICATION_REQUIRED"
    report = "RECOMMENDATION: PROCEED\n...\nRECOMMENDATION: HUMAN_CLARIFICATION_REQUIRED"
    assert parse_recommendation(report) == "HUMAN_CLARIFICATION_REQUIRED"

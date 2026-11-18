import json

import pytest

from scripts.approve_gate import record_decision


@pytest.fixture
def run(tmp_path):
    run = tmp_path / "CR-001"
    run.mkdir()
    gates = dict.fromkeys(["requirements", "plan", "review", "release"], "PENDING")
    (run / "factory-state.json").write_text(json.dumps({"human_gates": gates}))
    return run


def test_gate_requires_its_evidence(run):
    with pytest.raises(SystemExit, match="missing evidence"):
        record_decision(run, "requirements", "APPROVED", "Monserrat", "ok")


def test_gates_must_be_decided_in_order(run):
    (run / "02-plan.md").write_text("plan")
    with pytest.raises(SystemExit, match="'requirements' must be APPROVED"):
        record_decision(run, "plan", "APPROVED", "Ashley", "ok")


def test_rejected_gate_blocks_next_and_history_is_kept(run):
    (run / "01-intake-report.md").write_text("intake")
    (run / "02-plan.md").write_text("plan")
    record_decision(run, "requirements", "REJECTED", "Monserrat", "falta AC")
    with pytest.raises(SystemExit):
        record_decision(run, "plan", "APPROVED", "Ashley", "ok")
    record_decision(run, "requirements", "APPROVED", "Monserrat", "AC aclarado")
    record_decision(run, "plan", "APPROVED", "Ashley", "ok")

    state = json.loads((run / "factory-state.json").read_text())
    assert [d["decision"] for d in state["decision_log"]] == ["REJECTED", "APPROVED", "APPROVED"]
    assert state["decision_log"][-1]["role"] == "Tech Lead"


def test_decision_requires_name(run):
    (run / "01-intake-report.md").write_text("intake")
    with pytest.raises(SystemExit, match="name"):
        record_decision(run, "requirements", "APPROVED", " ", "ok")

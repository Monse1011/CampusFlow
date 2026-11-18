"""Dashboard tests. They never call Gemini."""

import json

import pytest
from fastapi.testclient import TestClient

from scripts import dashboard


@pytest.fixture
def run(tmp_path, monkeypatch):
    monkeypatch.setattr(dashboard, "RUNS", tmp_path)
    run = tmp_path / "CR-001"
    run.mkdir()
    gates = dict.fromkeys(["requirements", "plan", "review", "release"], "PENDING")
    state = {"change_id": "CR-001", "status": "AWAITING_REQUIREMENTS_DECISION"}
    state["human_gates"] = gates
    (run / "factory-state.json").write_text(json.dumps(state))
    (run / "01-intake-report.md").write_text("<script>alert(1)</script> RECOMMENDATION: PROCEED")
    return run


@pytest.fixture
def client(run):
    return TestClient(dashboard.app)


def test_run_page_shows_requirements_gate_form(client):
    body = client.get("/runs/CR-001").text
    assert "Product Owner (requirements)" in body
    assert "Registrar decisión" in body


def test_marks_evidence_to_read_and_new_files(client):
    body = client.get("/runs/CR-001").text
    assert "revisar para decidir" in body  # 01-intake-report.md for the requirements gate
    assert "nuevo" in body  # no decision yet, so every file is new


def test_decision_form_records_human_decision(client, run):
    form = {"gate": "requirements", "decision": "APPROVED", "by": "Monserrat", "reason": "ok"}
    response = client.post("/runs/CR-001/decision", data=form, follow_redirects=False)
    assert response.status_code == 303
    state = json.loads((run / "factory-state.json").read_text())
    assert state["human_gates"]["requirements"] == "APPROVED"
    assert state["decision_log"][0]["recorded_by"] == "Monserrat"


def test_cannot_decide_gate_that_is_not_waiting(client, run):
    form = {"gate": "plan", "decision": "APPROVED", "by": "Ashley", "reason": "ok"}
    page = client.post("/runs/CR-001/decision", data=form).text
    assert "no está esperando" in page
    state = json.loads((run / "factory-state.json").read_text())
    assert state["human_gates"]["plan"] == "PENDING"


def test_next_does_not_skip_human_gate(client, run):
    page = client.post("/runs/CR-001/next").text
    assert "Waiting for the Product Owner" in page
    assert not (run / "02-plan.md").exists()


def test_file_view_escapes_html_and_blocks_other_paths(client):
    body = client.get("/runs/CR-001/files/01-intake-report.md").text
    assert "<script>alert(1)</script>" not in body
    assert client.get("/runs/CR-001/files/..%2F..%2F.env").status_code == 404
    assert client.get("/runs/..%2F.env").status_code == 404

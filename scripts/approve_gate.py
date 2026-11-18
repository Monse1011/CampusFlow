from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Gates in the order they must be decided, with the human role that owns each one.
GATE_ROLES = {
    "requirements": "Product Owner",
    "plan": "Tech Lead",
    "review": "Human Reviewer",
    "release": "Release Manager",
}
# A human cannot decide on a gate without the evidence it is based on.
REQUIRED_EVIDENCE = {
    "requirements": ["01-intake-report.md"],
    "plan": ["02-plan.md"],
    "review": ["06-review-report.md", "07-security-report.md"],
    "release": ["factory-run.json", "traceability.md"],
}
VALID_DECISIONS = {"APPROVED", "MODIFIED", "REJECTED", "DEFERRED"}
PASSED = {"APPROVED", "MODIFIED"}


def record_decision(run: Path, gate: str, decision: str, by: str, reason: str) -> Path:
    if gate not in GATE_ROLES:
        raise SystemExit(f"Invalid gate: {list(GATE_ROLES)}")
    if decision not in VALID_DECISIONS:
        raise SystemExit(f"Invalid decision: {sorted(VALID_DECISIONS)}")
    if not by.strip() or not reason.strip():
        raise SystemExit("Human decision requires a name and a reason")
    state_path = run / "factory-state.json"
    if not state_path.exists():
        raise SystemExit(f"Run not found: {run.name}")
    state = json.loads(state_path.read_text(encoding="utf-8"))

    for previous in list(GATE_ROLES)[: list(GATE_ROLES).index(gate)]:
        if state["human_gates"][previous] not in PASSED:
            raise SystemExit(f"Gate {previous!r} must be APPROVED/MODIFIED before {gate!r}")
    missing = [name for name in REQUIRED_EVIDENCE[gate] if not (run / name).is_file()]
    if missing:
        raise SystemExit(f"Cannot decide {gate!r}: missing evidence {missing}")

    evidence = {
        "change_id": run.name,
        "gate": gate,
        "decision": decision,
        "reason": reason.strip(),
        "recorded_by": by.strip(),
        "role": GATE_ROLES[gate],
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }
    state["human_gates"][gate] = decision
    # Keep every decision so a REJECTED -> APPROVED sequence stays auditable.
    state.setdefault("decision_log", []).append(evidence)
    state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
    path = run / f"human-{gate}-decision.json"
    path.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    return path


def main() -> None:
    if len(sys.argv) < 6:
        raise SystemExit(
            'Usage: python scripts/approve_gate.py CR-001 plan APPROVED "Ashley" "reason"'
        )
    change_id, gate, decision, by = sys.argv[1:5]
    gate, decision = gate.lower(), decision.upper()
    reason = " ".join(sys.argv[5:])
    path = record_decision(ROOT / "runs" / change_id.upper(), gate, decision, by, reason)
    print(f"Recorded {gate}: {decision} by {by} ({GATE_ROLES[gate]}) -> {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

"""Local dashboard for factory runs: view evidence, record human decisions, run the next stage.

It reuses approve_gate.record_decision and run_factory.advance, so the rules are the same as
in the CLI. Listens on 127.0.0.1 only.

    uv run python scripts/dashboard.py   ->  http://127.0.0.1:8000
"""

from __future__ import annotations

import html
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi import FastAPI, Form, HTTPException  # noqa: E402
from fastapi.responses import HTMLResponse, RedirectResponse  # noqa: E402

from scripts.approve_gate import (  # noqa: E402
    GATE_ROLES,
    REQUIRED_EVIDENCE,
    VALID_DECISIONS,
    record_decision,
)
from scripts.run_factory import STAGES, advance, next_stage  # noqa: E402

RUNS = ROOT / "runs"
TEAM = ["Ashley", "Monserrat", "Osmar"]  # shortcut: duplicated from docs/HUMAN_ROLES.md
WAITING_GATE = {"await_requirements": "requirements", "await_plan": "plan"}
STAGE_LABELS = {
    "intake": "Ejecutar Intake Agent",
    "plan": "Ejecutar Planner Agent",
}
CR_ID = re.compile(r"^CR-[A-Za-z0-9-]+$")

app = FastAPI(title="CampusFlow Factory")

STYLE = """
:root { --bg:#f7f7f8; --card:#fff; --text:#1d1d1f; --muted:#6e6e73; --line:#e3e3e6;
  --accent:#1a5fd1; --ok:#1e7f3c; --warn:#a35a00; --bad:#b3261e; }
@media (prefers-color-scheme: dark) { :root { --bg:#151517; --card:#1f1f22; --text:#ececef;
  --muted:#a1a1a6; --line:#34343a; --accent:#6ea0ff; --ok:#5cc47a; --warn:#f0a840;
  --bad:#ff7b72; } }
body { margin:0; background:var(--bg); color:var(--text);
  font:15px/1.5 -apple-system, system-ui, sans-serif; }
main { max-width:960px; margin:0 auto; padding:24px 16px 64px; }
a { color:var(--accent); }
h1 { font-size:22px; margin:0 0 4px; } h2 { font-size:16px; margin:0 0 12px; }
.card { background:var(--card); border:1px solid var(--line); border-radius:10px;
  padding:16px; margin:16px 0; }
.muted { color:var(--muted); }
.gates { display:flex; flex-wrap:wrap; gap:8px; }
.gate { border:1px solid var(--line); border-radius:999px; padding:4px 12px; font-size:13px; }
.APPROVED, .MODIFIED { color:var(--ok); border-color:var(--ok); }
.REJECTED { color:var(--bad); border-color:var(--bad); }
.DEFERRED, .PENDING { color:var(--warn); }
.tag { font-size:12px; border-radius:4px; padding:1px 6px; margin-left:6px; }
.tag.new { background:var(--accent); color:#fff; }
.tag.read { border:1px solid var(--warn); color:var(--warn); }
.msg { border-left:4px solid var(--accent); }
.msg.error { border-left-color:var(--bad); }
label { display:block; margin:10px 0 4px; font-weight:600; }
input[type=text], textarea { width:100%; box-sizing:border-box; padding:8px;
  border:1px solid var(--line); border-radius:6px; background:var(--bg); color:var(--text);
  font:inherit; }
textarea { min-height:80px; }
.radios label { display:inline-block; font-weight:400; margin-right:16px; }
button { margin-top:14px; padding:9px 16px; border:0; border-radius:6px;
  background:var(--accent); color:#fff; font:inherit; font-weight:600; cursor:pointer; }
button:disabled { opacity:.6; cursor:wait; }
pre { white-space:pre-wrap; word-wrap:break-word; background:var(--bg); padding:12px;
  border-radius:6px; border:1px solid var(--line); font-size:13px; }
table { width:100%; border-collapse:collapse; font-size:14px; }
td, th { text-align:left; padding:6px 8px; border-bottom:1px solid var(--line); }
"""


def page(title: str, body: str) -> HTMLResponse:
    return HTMLResponse(
        f"<!doctype html><html lang='es'><head><meta charset='utf-8'>"
        f"<meta name='viewport' content='width=device-width, initial-scale=1'>"
        f"<title>{html.escape(title)}</title><style>{STYLE}</style></head>"
        f"<body><main>{body}</main></body></html>"
    )


def load_run(cr: str) -> tuple[Path, dict]:
    if not CR_ID.match(cr):
        raise HTTPException(404, "Run not found")
    run = RUNS / cr
    state_path = run / "factory-state.json"
    if not state_path.is_file():
        raise HTTPException(404, "Run not found")
    return run, json.loads(state_path.read_text(encoding="utf-8"))


def message_card(msg: str, error: bool) -> str:
    if not msg:
        return ""
    return f"<div class='card msg{' error' if error else ''}'>{html.escape(msg)}</div>"


@app.get("/", response_class=HTMLResponse)
def index() -> HTMLResponse:
    rows = []
    for state_path in sorted(RUNS.glob("CR-*/factory-state.json")):
        state = json.loads(state_path.read_text(encoding="utf-8"))
        cr = state_path.parent.name
        rows.append(
            f"<tr><td><a href='/runs/{cr}'>{cr}</a></td>"
            f"<td>{html.escape(state.get('status', ''))}</td></tr>"
        )
    table = "".join(rows) or "<tr><td colspan=2 class='muted'>Sin runs todavía.</td></tr>"
    return page(
        "CampusFlow Factory",
        "<h1>CampusFlow Factory</h1><p class='muted'>Runs en <code>runs/</code></p>"
        f"<div class='card'><table><tr><th>Change Request</th><th>Estado</th></tr>"
        f"{table}</table></div>",
    )


@app.get("/runs/{cr}", response_class=HTMLResponse)
def run_view(cr: str, msg: str = "", error: bool = False) -> HTMLResponse:
    run, state = load_run(cr)
    stage = next_stage(run, state)
    gates = "".join(
        f"<span class='gate {html.escape(value)}'>{GATE_ROLES[gate]}: {html.escape(value)}</span>"
        for gate, value in state["human_gates"].items()
    )
    log_entries = state.get("decision_log", [])
    # "Nuevo" = changed after the last human decision (1 s margin: the decision's own files).
    since = 0.0
    if log_entries:
        since = datetime.fromisoformat(log_entries[-1]["recorded_at"]).timestamp() + 1
    waiting = WAITING_GATE.get(stage)
    must_read = set(REQUIRED_EVIDENCE[waiting]) if waiting else set()

    def file_row(p: Path) -> str:
        tags = "<span class='tag new'>nuevo</span>" if p.stat().st_mtime > since else ""
        if p.name in must_read:
            tags += "<span class='tag read'>revisar para decidir</span>"
        link = f"<a href='/runs/{cr}/files/{quote(p.name)}'>{html.escape(p.name)}</a>"
        return f"<tr><td>{link} {tags}</td></tr>"

    files = "".join(file_row(p) for p in sorted(run.iterdir()) if p.is_file())

    action = ""
    if stage in STAGES:
        action = (
            f"<div class='card'><h2>Siguiente etapa automática</h2>"
            f"<form method='post' action='/runs/{cr}/next' onsubmit='busy(this)'>"
            f"<button>▶ {STAGE_LABELS[stage]}</button>"
            f"<p class='muted'>Llama a Gemini; puede tardar 1–5 min.</p></form></div>"
        )
    elif stage in WAITING_GATE:
        gate = WAITING_GATE[stage]
        radios = "".join(
            f"<label><input type='radio' name='decision' value='{d}' required> {d}</label>"
            for d in sorted(VALID_DECISIONS)
        )
        team = "".join(f"<option value='{name}'>" for name in TEAM)
        action = (
            f"<div class='card'><h2>⛔ Decisión humana: {GATE_ROLES[gate]} ({gate})</h2>"
            f"<p class='muted'>La fábrica está detenida. Lee antes de decidir: "
            + ", ".join(
                f"<a href='/runs/{cr}/files/{quote(name)}'>{name}</a>"
                for name in REQUIRED_EVIDENCE[gate]
            )
            + "</p>"
            f"<form method='post' action='/runs/{cr}/decision' onsubmit='busy(this)'>"
            f"<input type='hidden' name='gate' value='{gate}'>"
            f"<label for='by'>Nombre</label>"
            f"<input type='text' id='by' name='by' list='team' required>"
            f"<datalist id='team'>{team}</datalist>"
            f"<label>Decisión</label><div class='radios'>{radios}</div>"
            f"<label for='reason'>Motivo</label>"
            f"<textarea id='reason' name='reason' required></textarea>"
            f"<button>Registrar decisión</button></form></div>"
        )
    else:
        action = "<div class='card muted'>Siguiente etapa: Coder (todavía no implementado).</div>"

    log = "".join(
        f"<tr><td>{html.escape(d['recorded_at'][:16].replace('T', ' '))}</td>"
        f"<td>{html.escape(d['gate'])}</td>"
        f"<td><span class='gate {html.escape(d['decision'])}'>"
        f"{html.escape(d['decision'])}</span></td>"
        f"<td>{html.escape(d['recorded_by'])} ({html.escape(d['role'])})</td>"
        f"<td>{html.escape(d['reason'])}</td></tr>"
        for d in log_entries
    )
    log_card = (
        f"<div class='card'><h2>Historial de decisiones</h2><table>"
        f"<tr><th>Fecha (UTC)</th><th>Gate</th><th>Decisión</th><th>Quién</th><th>Motivo</th></tr>"
        f"{log}</table></div>"
        if log
        else ""
    )
    script = (
        "<script>function busy(f){const b=f.querySelector('button');"
        "b.disabled=true;b.textContent='Procesando…';}</script>"
    )
    return page(
        cr,
        f"<p><a href='/'>← Runs</a></p><h1>{cr}</h1>"
        f"<p class='muted'>Estado: <strong>{html.escape(state['status'])}</strong></p>"
        f"{message_card(msg, error)}"
        f"<div class='card'><h2>Gates humanos</h2><div class='gates'>{gates}</div></div>"
        f"{action}"
        f"<div class='card'><h2>Evidencia</h2><table>{files}</table></div>"
        f"{log_card}{script}",
    )


@app.get("/runs/{cr}/files/{name}", response_class=HTMLResponse)
def file_view(cr: str, name: str) -> HTMLResponse:
    run, _ = load_run(cr)
    # Only files that actually exist in this run folder; no paths.
    allowed = {p.name: p for p in run.iterdir() if p.is_file()}
    if name not in allowed:
        raise HTTPException(404, "File not found")
    text = allowed[name].read_text(encoding="utf-8")
    return page(
        f"{cr} · {name}",
        f"<p><a href='/runs/{cr}'>← {cr}</a></p><h1>{html.escape(name)}</h1>"
        f"<pre>{html.escape(text)}</pre>",
    )


def back(cr: str, msg: str, error: bool) -> RedirectResponse:
    # Redirect after POST so a browser refresh does not repeat the action.
    url = f"/runs/{cr}?msg={quote(msg)}" + ("&error=true" if error else "")
    return RedirectResponse(url, status_code=303)


@app.post("/runs/{cr}/decision")
def decision(
    cr: str, gate: str = Form(...), decision: str = Form(...), by: str = Form(...),
    reason: str = Form(...),
) -> RedirectResponse:
    run, state = load_run(cr)
    if WAITING_GATE.get(next_stage(run, state)) != gate:
        return back(cr, f"El gate {gate!r} no está esperando una decisión.", True)
    try:
        record_decision(run, gate, decision.upper(), by, reason)
    except SystemExit as rule:
        return back(cr, str(rule), True)
    return back(cr, f"Decisión registrada: {gate} {decision.upper()} por {by}.", False)


@app.post("/runs/{cr}/next")
def next_step(cr: str) -> RedirectResponse:
    run, _ = load_run(cr)
    ok, message = advance(run)
    return back(cr, message, not ok)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)

# Architecture

## Product

```text
FastAPI adapter
      |
      v
CampusFlowService        <- business rules
      |
      v
SQLiteCampusFlowRepository
      |
      v
SQLite
```

Rules: API does not implement business policy; Repository does not decide business policy; Service coordinates behavior.

## Factory

### Flujo

Cada flecha `⛔` es un gate humano: la fábrica se detiene y no continúa hasta que una persona
registra su decisión con `scripts/approve_gate.py`.

```text
CHANGE_REQUEST.md
      |
[Intake Agent] ---------- HUMAN_CLARIFICATION_REQUIRED --> ⛔ STOP (no planifica)
      |
⛔ GATE 1a — Product Owner: requirements
      |
[Planner Agent] <-------- plan REJECTED (re-planifica con el motivo)
      |
⛔ GATE 1b — Tech Lead: plan
      |
[Coder Agent]  <---------------------------+
      |                                    |
[Test Analyst Agent]                       |
      |                                    |
[Verification Gate] -- FAIL ---------------+   (pytest + ruff + repo checks; determinista)
      | PASS
      +---------------------+
[Reviewer Agent]      [Security Agent]         (sesiones separadas, read-only)
      +---------------------+
      |
⛔ GATE 2 — Human Reviewer: ACCEPTED / REJECTED / MODIFIED / DEFERRED por finding
      |
  findings bloqueantes? -- sí --> Coder Fix -> Re-verification -> Re-review --> GATE 2
      | no
[Evidence] -> evidence-summary.md + traceability.md + factory-run.json
      |
⛔ GATE 3 — Release Manager: READY FOR HUMAN MERGE / NOT READY
      |
Merge: exclusivamente humano. Ningún agente hace merge.
```

### Máquina de estados

El estado vive en `runs/<CR-ID>/factory-state.json`, no en la conversación.
`scripts/run_factory.py <CR-ID>` lee el estado, ejecuta **una sola etapa** y se detiene en el
siguiente gate. Si una etapa falla (p. ej. 429/503 de Gemini), el estado no avanza y basta con
volver a ejecutar el comando (checkpoint + resume).

| Estado | Siguiente acción | Quién |
|--------|------------------|-------|
| `INTAKE_PENDING` | Intake Agent → `01-intake-report.md` | Fábrica |
| `AWAITING_HUMAN_CLARIFICATION` | Aclarar el CR (ambigüedad) | Product Owner |
| `AWAITING_REQUIREMENTS_DECISION` | `approve_gate.py <CR> requirements ...` | Product Owner |
| requirements APPROVED/MODIFIED | Planner Agent → `02-plan.md` | Fábrica |
| `AWAITING_PLAN_DECISION` | `approve_gate.py <CR> plan ...` | Tech Lead |
| plan APPROVED/MODIFIED | Coder Agent (pendiente) | Fábrica |

Reglas de `approve_gate.py`: los gates se deciden en orden; cada gate exige su evidencia
(p. ej. `requirements` exige `01-intake-report.md`); toda decisión registra nombre, rol, motivo
y fecha, y se agrega a `decision_log` (no se sobrescribe).

### Agentes

Cada agente corre en una **sesión ADK nueva**: ningún agente recibe la conversación ni el
razonamiento de otro, solo los artifacts en `runs/<CR-ID>/`. Modelo: `gemini-3.8-flash`.

| Agente | Responsabilidad | Herramientas permitidas | Prohibido | Salida | Se detiene si... | Estado |
|--------|-----------------|-------------------------|-----------|--------|------------------|--------|
| Intake | Analiza el CR, AC afectados y ambigüedad | `list_repo_files`, `read_repo_file` (solo lectura) | Escribir archivos, diseñar la solución | `01-intake-report.md` + `RECOMMENDATION` | El CR es ambiguo o contradice requisitos | Implementado |
| Planner | Plan técnico con TASK-xx → AC, archivos y tests | Solo lectura | Escribir código, cambiar requisitos | `02-plan.md` | Queda ambigüedad | Implementado |
| Coder | Implementa únicamente el plan aprobado | Lectura + escritura acotada a `campusflow/` y `tests/` | Ejecutar sin plan aprobado, editar docs/requisitos, auto-aprobarse | Código + `04-coder-report.md` | Plan sin aprobar, cambio fuera del plan | Pendiente (M2) |
| Test Analyst | Gaps de pruebas: negativos, boundary, regresión | Lectura + escritura solo en `tests/` + verificación | Modificar código de la app, debilitar tests, declarar PASS | `test-analysis.md` + tests | Requiere cambiar código de la app | Pendiente (M2) |
| Reviewer | Revisión independiente contra requisitos, arquitectura, diff y tests | Solo lectura | Editar código, cambiar requisitos, hacer merge | `06-review-report.md` (MUST/SHOULD FIX) | Evidencia insuficiente, conflicto de requisitos | Pendiente (M3) |
| Security | SAST/SCA/secrets + riesgos de agentes | Solo lectura + Semgrep, pip-audit, secret scan | Editar código de la app | `07-security-report.md` | Hallazgo HIGH sin decisión humana | Pendiente (M3) |
| Evidence | Consolida evidencia real del run | Lectura + escritura solo en `runs/<CR-ID>/` | Inventar evidencia, decidir el release | `traceability.md`, `factory-run.json` | Falta evidencia | Pendiente (M4) |

Los permisos se imponen en código (`factory_app/tools.py`): las lecturas están limitadas a
`docs/`, `change_requests/`, `campusflow/`, `tests/` y `runs/`, y no pueden salir del repo.
`.env` no es legible por ningún agente.

### Contexto

Los agentes no reciben el repositorio completo. Parten de `docs/REPO_MAP.md` y leen solo lo
necesario; cada lectura queda registrada en `runs/<CR-ID>/context-trace.json`.
El contenido del CR se entrega delimitado como datos no confiables, no como instrucciones.

### Resiliencia (Free Tier)

`factory_app/agents.py`: reintentos con backoff exponencial ante 429/500/503/504 (4 intentos)
y timeout de 60 s por llamada. Los agentes corren secuencialmente; no se usan varias API keys.

The Reviewer must inspect requirements, architecture, changed code, tests, verification evidence
and actual APIs/dependencies. It must not treat the Coder's own claims as proof.

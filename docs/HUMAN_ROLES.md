# Human Roles

## Equipo

- **Ashley** — Aguilar Moreno Ashley Shaden
- **Monserrat** — Anaya Alva Monserrat
- **Osmar** — Ciau Martin Osmar Ruben

Equipo de 3 personas y 4 roles: en cada CR una persona cubre Product Owner + Release Manager
(ambos son decisiones de negocio: qué se pide y si está listo). Los roles rotan entre CRs.
Cada decisión humana se registra con `scripts/approve_gate.py` (nombre + rol + motivo).

| Rol | Gate | Decide |
|-----|------|--------|
| Product Owner | Gate 1 (requisitos) | Interpretación del CR y criterios de aceptación |
| Tech Lead | Gate 1 (plan) | Plan, arquitectura, alcance |
| Human Reviewer | Gate 2 (findings) | ACCEPTED / REJECTED / MODIFIED / DEFERRED por finding |
| Release Manager | Gate 3 (release) | READY FOR HUMAN MERGE / NOT READY |

## Rotación

| CR | Product Owner | Tech Lead | Human Reviewer | Release Manager |
|----|---------------|-----------|----------------|-----------------|
| CR-001 | Monserrat | Ashley | Osmar | Monserrat |
| CR-003 | Ashley | Osmar | Monserrat | Ashley |
| CR-002 / CR-005 | Osmar | Monserrat | Ashley | Osmar |
| CR sorpresa | Monserrat | Ashley | Osmar | Monserrat |

Regla: quien fue Tech Lead (aprobó el plan) no es Human Reviewer del mismo CR.

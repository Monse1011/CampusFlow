# CampusFlow Requirements

## FR-01 — Events
Organizers can create events with title, capacity (>0) and owner identifier.

- AC-01.1: created event receives a unique integer ID.
- AC-01.2: capacity <= 0 is rejected.

## FR-02 — Event discovery
Users can list existing events.

- AC-02.1: list exposes ID, title, capacity and owner.

## FR-03 — Registration
A user can register while capacity is available.

- AC-03.1: unknown event is rejected.
- AC-03.2: available capacity -> registration accepted.
- AC-03.3: full capacity -> registration is stored as `WAITLISTED` (FIFO), not rejected.
  The API answers `201` with status `ACTIVE` or `WAITLISTED`; capacity no longer returns `409`.
  The waitlist has no limit.

> AC-03.3 changed by CR-001 (waitlist). Previous text: "full capacity -> baseline rejects
> registration." Approved by the Product Owner (Monserrat, 2026-11-18):
> `runs/CR-001/human-requirements-decision.json`.

## FR-04 — Cancellation
A registered user can cancel an existing registration.

- AC-04.1: existing registration is removed.
- AC-04.2: missing registration is reported clearly.
- AC-04.3 (CR-001): cancelling an `ACTIVE` registration promotes the first `WAITLISTED` user.
  Cancelling a `WAITLISTED` registration promotes no one.

## NFR-01 — Architecture
Business rules live in Service. Dependency direction: `API -> Service -> Repository`.

## NFR-02 — Verification
Business-rule changes require automated tests.

## NFR-03 — Security
Secrets stay out of source control. Agent roles follow least privilege.

## NFR-04 — Evidence
Each factory run is auditable under `runs/<CR-ID>/`.

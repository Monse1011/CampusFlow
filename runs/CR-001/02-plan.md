# Implementation Plan - CR-001: Event Waitlist

Implement a waitlist system where registrations beyond an event's capacity are marked as `WAITLISTED`. When an `ACTIVE` participant cancels, the next person on the waitlist (FIFO) is automatically promoted to `ACTIVE`.

## User Review Required

> [!IMPORTANT]
> - **Schema Migration**: The plan assumes that modifying `_create_schema` in `repository.py` is sufficient for the `registrations` table update. If the database file `campusflow.db` already exists on disk with the old schema, it may need to be deleted or manually migrated.
> - **API Change**: The `POST /events/{id}/registrations` endpoint will no longer return `409 Conflict` when an event is full; it will return `201 Created` with a `status` field.

## Proposed Changes

### Domain & Repository (`campusflow/domain.py`, `campusflow/repository.py`)
- Define `RegistrationStatus` constants (e.g., `"ACTIVE"`, `"WAITLISTED"`).
- Update `Registration` dataclass to include a `status` field.
- Update `registrations` table schema to include a `status` column (defaulting to `'ACTIVE'` for existing rows if any, but we'll manage it explicitly).
- Enhance `SQLiteCampusFlowRepository`:
    - `add_registration`: Accept and store `status`.
    - `count_active_registrations`: Count only registrations with `status='ACTIVE'`.
    - `get_registration`: Fetch a registration by `event_id` and `user_id` (to check its status before deletion).
    - `get_next_waitlisted_user`: Retrieve the oldest `WAITLISTED` user for an event (FIFO using `id`).
    - `update_registration_status`: Change a user's status (used for promotion).

### Service Layer (`campusflow/service.py`)
- **`register`**:
    - Calculate current occupancy using `count_active_registrations`.
    - If `occupancy < event.capacity`, set status to `ACTIVE`.
    - Otherwise, set status to `WAITLISTED`.
    - Return the created `Registration` object.
- **`cancel`**:
    - Fetch the registration to check its status before deletion.
    - Delete the registration.
    - If the deleted registration was `ACTIVE`, find the next `WAITLISTED` user via the repository and promote them to `ACTIVE`.
    - If the registration was `WAITLISTED`, do nothing further.

### API Layer (`campusflow/api.py`)
- Update `register` endpoint:
    - Remove `CapacityReachedError` exception handling as the service will no longer raise it.
    - The `201 Created` response will now naturally include the `status` field in the JSON body.

## Detailed Tasks

| Task | Description | AC |
| :--- | :--- | :--- |
| **TASK-01** | **Domain & Repository Updates**: Add `status` field to `Registration` and DB schema. Implement status-aware repository methods (`count_active`, `get_next_waitlisted`, `update_status`). | AC-CR001.1, AC-CR001.2, AC-CR001.3 |
| **TASK-02** | **Service Logic (Registration)**: Update `register()` to assign `ACTIVE` or `WAITLISTED` status instead of raising `CapacityReachedError`. | AC-CR001.1, AC-CR001.2 |
| **TASK-03** | **Service Logic (Promotion)**: Update `cancel()` to identify the status of the cancelled registration and promote the next waitlisted user if needed. | AC-CR001.4 |
| **TASK-04** | **API Alignment**: Remove the 409 error handler for `CapacityReachedError` in `api.py`. | Req (1) |
| **TASK-05** | **Testing**: Update existing service tests and add new scenarios for FIFO ordering and promotion logic. | AC-CR001.5 |

## Verification Plan

### Automated Tests
Run the updated and new tests using `pytest`:
```bash
# Verify service logic and regressions
pytest tests/product/test_service.py
```

### Manual Verification Scenarios (via Service/API)
1. **Full Capacity**: Create event (cap 1). Register User A (ACTIVE). Register User B (WAITLISTED).
2. **Promotion**: Cancel User A. Verify User B is now ACTIVE.
3. **Waitlist Cancellation**: Create event (cap 1). Register A (ACTIVE), B (WAITLISTED), C (WAITLISTED). Cancel B. Verify A is still ACTIVE and C is still WAITLISTED.
4. **FIFO Order**: Register A, B, C for a cap-1 event. Cancel A. Verify B is promoted (not C).

## Assumptions & Constraints
- FIFO is guaranteed by the `id` (autoincrement) in the `registrations` table.
- A user cannot be "double promoted" if multiple slots open; the logic handles one promotion per cancellation.
- Business rules are strictly kept within the `Service` layer as requested.
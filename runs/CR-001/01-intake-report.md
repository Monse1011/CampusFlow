# Intake Report - CR-001: Event Waitlist

## Requested Outcome
Implement a waitlist feature for events. When an event reaches its capacity, subsequent registrations should be placed on a FIFO waitlist. If an active participant cancels their registration, the first person on the waitlist should be automatically promoted to an active participant.

## Relevant Requirements/AC
- **FR-03 (Updated by CR-001):** Registration now supports waitlisting instead of immediate rejection when full.
- **AC-CR001.1:** Registrations made when an event is below capacity remain `ACTIVE`.
- **AC-CR001.2:** Registrations made when an event is at capacity are marked as `WAITLISTED`.
- **AC-CR001.3:** The waitlist must follow First-In-First-Out (FIFO) order.
- **AC-CR001.4:** Cancelling an active registration triggers the promotion of the first user on the waitlist.
- **AC-CR001.5:** Baseline behaviors (listing events, creating events) must remain stable.

## Ambiguity/Conflict
- **Status Representation:** The current `Registration` entity and `registrations` database table do not have a `status` field. This will need to be introduced.
- **API Impact:** `CapacityReachedError` currently maps to a `409 Conflict` in the API. If waitlisting is implemented, `service.register` may no longer raise this error for full events, potentially changing the API's response behavior (e.g., returning `201 Created` with a status). The constraint specifies business rules remain in `Service`.
- **Waitlisted User Cancellation:** While not explicitly detailed, it is assumed that waitlisted users can also cancel their waitlist spot without triggering further promotions.
- **Waitlist Capacity:** There is no specified limit for the waitlist size; it is assumed to be unbounded for now.
- **Promotion Logic:** The requirement implies automatic promotion during the cancellation process within the Service layer.

## Likely Repository Areas
- **`campusflow/domain.py`**: Define registration statuses (e.g., `ACTIVE`, `WAITLISTED`).
- **`campusflow/repository.py`**: 
    - Update `registrations` table schema to include a `status` column.
    - Update `add_registration` and `list_registrations`.
    - Add/update methods to support finding and promoting waitlisted users.
- **`campusflow/service.py`**: 
    - Update `register()` to handle waitlist logic instead of raising `CapacityReachedError`.
    - Update `cancel()` to handle automatic promotion of the next waitlisted user.
- **`tests/product/test_service.py`**: Update existing tests and add new deterministic tests for waitlist transitions and promotion scenarios.

## Recommendation
PROCEED

RECOMMENDATION: PROCEED
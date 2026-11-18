# CampusFlow Specification

References `REQUIREMENTS.md`; does not redefine it.

## Event creation
Valid input creates an Event; invalid capacity is rejected. Covers FR-01.

## List events
Returns current events in ID order. Covers FR-02.

## Register
- unknown event -> `EventNotFoundError`;
- space available -> registration stored with status `ACTIVE`;
- full -> registration stored with status `WAITLISTED`, in FIFO order (AC-03.3, CR-001).
  `CapacityReachedError` is no longer raised for a full event.

Known starter gap: duplicate registration is not prevented. CR-003 addresses it.

## Cancel
Existing registration is removed; missing registration -> `RegistrationNotFoundError`.
Cancelling an `ACTIVE` registration promotes the oldest `WAITLISTED` one to `ACTIVE`;
cancelling a `WAITLISTED` registration promotes no one (AC-04.3, CR-001).

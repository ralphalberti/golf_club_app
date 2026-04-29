# Backlog

---

## RSVP / Workflow

### Simplify RSVP State Model

- [ ] Replace current status system with:
  - `selected`
  - `invited`
  - `yes`
- [ ] Remove:
  - `no`
  - `maybe`
- [ ] Rules:
  - `selected` → chosen but not emailed
  - `invited` → email sent
  - `yes` → confirmed playing
  - all others → not playing (no tracking needed)
- [ ] Update:
  - database constraint (`outing_rsvps.status`)
  - service logic
  - UI labels
  - workflow summary alignment

---

### Remove Invited Member

- [ ] Allow removing a member from invitation list
- [ ] Delete corresponding `outing_rsvps` row
- [ ] Only allowed before emails are sent
- [ ] Disable/remove button after email send stage
- [ ] Optional:
  - double-click removal with confirmation dialog

---

### Pre-Invitation State (UI Alignment)

- [ ] Introduce `selected` state in UI
- [ ] Rename or clarify:
  - "Invited / Confirmed Members" pane
- [ ] Ensure Workflow Summary matches actual state:
  - preparing draft happens before "invited"

---

## Scheduling

### Waitlist Behavior (Future Enhancement)

- [ ] Consider persisting waitlist position explicitly
- [ ] Handle:
  - re-confirmation (YES → NO → YES)
  - priority rules

---

## UI / UX Improvements

### RSVP Dialog Improvements

- [ ] Improve clarity between:
  - Active Members (left pane)
  - Selected / Invited / Confirmed (right pane)
- [ ] Prevent duplicate conceptual states
- [ ] Improve visual feedback for:
  - selected vs invited vs confirmed

---

## System / Architecture

### Service → Repository Refactor

- [ ] Move DB logic out of `RsvpService` into repository layer
- [ ] Ensure:
  - services = business logic only
  - repositories = SQL only
- [ ] Remove duplicate logic between layers

---

## Notes

- Focus first on:
  - completing end-to-end RSVP → Schedule flow
  - stabilizing current system
- All items above should be implemented in **separate feature branches**

---

### Disable Manual Member Invitation from RSVP Dialog

- [ ] Disable double-click behavior from Active Members pane
- [ ] Keep manual move controls hidden or admin/test-only
- [ ] Invitation list should be populated by invitation workflow
- [ ] Eligible recipients should be all active, non-suspended members
- [ ] Ensure selecting/moving members does not remove them from email recipient pool before invitations are sent

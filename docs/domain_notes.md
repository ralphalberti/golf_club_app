# Golf Club Domain Notes (v2)

## Active Development Database

Primary active development database:

- `data/golf_club.db`

Legacy/development database files may still exist, including:

- `app.db`
- backup database snapshots under `data/`

The desktop application and RSVP HTTP server must both point to the same active database.
When RSVP behavior changes, restart the RSVP server before testing email-link flows.

---

## Tee Time Allocation

- Each course provides a fixed number of tee times to the club
- This is the **default allocation**
- Example:
  - Calusa: 11 tee times
  - Rosedale: 8 tee times

- Courses hold these tee times until notified
- Unused tee times are released back to the course

### System Design

- courses.default_tee_time_count
- outings.tee_time_count (snapshot)

- Scheduler should:
  - use minimum number of tee times required
  - prefer foursomes
  - place threesomes early
  - leave unused tee times empty

---

## Green Fees

- Negotiated per course
- Valid for a time period
- Change seasonally

- course_fee_schedules table:
  - course_id
  - fee
  - effective_start_date
  - effective_end_date

- outings.fee:
  - snapshot at time of creation
  - used in invitations

---

## RSVP Process

### Updated Model (v2)

1. Outing created
2. Invitations sent automatically at ~5 PM on outing day
3. Members respond via **RSVP link (email)**
4. Only "yes" players are schedulable

### Key Change

- RSVP responses are **link-driven**, not email-parsed
- Eliminates ambiguity and ensures accurate timestamps

---

## RSVP Link System

### Overview

- Each member receives a **unique RSVP link**
- Example:

  <https://localhost:8000/rsvp/yes?token=XYZ>

- Token encodes:
  - outing_id
  - member_id
  - signature (HMAC)

### Behavior

- Clicking link:
  - validates token
  - records RSVP = "yes"
  - sets `responded_at` timestamp

### Constraints

- First valid "yes" click determines priority
- Repeated clicks should not overwrite original timestamp

### Important Persistence Rule

RSVP email-link clicks must create RSVP rows if none exist.

Implementation detail:

- RSVP email handlers use `record_yes_if_first()`
- RSVP email handlers must not rely on `set_member_rsvp_status()` for first-click YES recording

Reason:

- Email invitations may be sent before explicit RSVP rows exist for every recipient
- First RSVP click must create the row and preserve original timestamp ordering

---

## RSVP Priority & Waitlist

### Status: ACTIVE

### Core Principle

Scheduling priority is determined by RSVP "yes" timestamp for MEMBERS.

Guests do not independently participate in RSVP priority ordering.

### Scheduling Priority

- First-come-first-served ordering
- Earlier RSVP timestamps receive scheduling priority
- Repeat RSVP clicks must not overwrite original timestamps

### Member Scheduling

Members are scheduled first until tee-sheet capacity is exhausted.

### Guest Scheduling

Guests are evaluated only after member scheduling completes.

Guests:

- may fill unused slots
- must remain attached to sponsor
- must not displace members
- should preferentially occupy later tee times

### Waitlist Behavior

Waitlist applies to RSVP-yes members who could not be scheduled.

Guests may remain unscheduled even when their sponsor is scheduled.

---

## Guests

- Guests are tied to a sponsoring member
- A member may bring multiple guests

### Important Rules

- Guests do not have independent scheduling priority
- Guests must never displace RSVP-yes members
- Guests may only occupy leftover tee-sheet capacity
- Guests must remain attached to their sponsor if scheduled
- Guests should generally appear in later tee times

### Scheduling Model

Scheduling occurs in two passes:

1. Members are scheduled first
2. Guests are attached afterward where capacity permits

### Capacity Rules

Examples:

- 4 open slots remaining
  - sponsor + 2 guests may fit

- 2 open slots remaining
  - sponsor + 2 guests cannot fit
  - guests remain unscheduled

- Guests must never create fivesomes

---

## Schedule Visibility

- All active, non-suspended members can view schedules
- Encourages late fill-in participation

---

## Email Workflow (NEW)

### Overview

Outing communication follows a structured lifecycle:

### 1. Invitation Email (Automated)

- Sent at ~5 PM on outing day
- Sent to all active members via BCC
- Contains:
  - outing date
  - course
  - greens fee
  - RSVP link

### 2. Tee-Time Request (Course)

- Sent ~2 days after invitation
- Purpose:
  - inform course of required tee times
- Based on RSVP "yes" count

### 3. Draft Schedule (Members)

- Sent after initial scheduling
- Shows:
  - tee times
  - player groupings
  - open slots

### 4. Revised Schedule (Members)

- Sent after late changes / cancellations

### 5. Final Schedule (Course)

- Sent after finalization
- Operational document for course

---

## Email Template System (NEW)

- Emails are template-based
- Templates include:
  - subject
  - body
  - variable placeholders

### Variables

- outing_date
- course_name
- fee
- RSVP link

### Admin Customization

- Admins can:
  - modify body before sending
  - add custom notes (e.g., announcements)

---

## Invitation Preview Mode (NEW)

### Purpose

- Prevent accidental emails during development/testing

### Behavior

- Emails are written to file instead of sent
- Location:

  exports/preview/

- Includes:
  - recipient
  - subject
  - body
  - RSVP link

---

## Scheduling Units

### Definition

A Scheduling Unit represents:

- a sponsor member
- plus any confirmed guests attached to that sponsor

### Important Clarification

Scheduling priority belongs to RSVP-yes MEMBERS only.

Guests never independently compete for tee-sheet capacity.

### Core Scheduling Rules

1. RSVP-yes members are scheduled first
2. Guests must never displace RSVP-yes members
3. Guests may only fill leftover/open tee-sheet capacity
4. Guests must remain attached to their sponsoring member
5. Guest-containing groups should be placed in later tee times when possible

### Operational Behavior

Initial schedule generation works in two phases:

#### Phase 1 — Member Scheduling

- RSVP-yes members are scheduled by RSVP priority
- Scheduler optimizes:
  - foursomes
  - fairness
  - pairing variety
  - tee-time balance

#### Phase 2 — Guest Attachment

After members are scheduled:

- sponsors with confirmed guests are evaluated
- guests are attached only if:
  - open slots remain
  - sponsor tee time has sufficient capacity
  - adding guests does not displace members
  - no fivesomes are created

### Important Constraint

A guest cannot be scheduled unless their sponsor is already scheduled.

### Waitlist Behavior

Waitlist priority applies to members only.

Guests are dependent additions and may remain unscheduled even when their sponsor is scheduled.

---

## Cancellation Rules (Future)

- <24h: 3-week suspension
- <48h: 1-week suspension
- >2 cancellations in 6 months: termination

---

## Workflow Awareness

Admin must always know:

- where they are in the process
- what step comes next
- what actions are pending

### Suggested Workflow States

- draft
- invites_sent
- rsvp_open
- schedule_draft
- schedule_final
- completed

---

## Future Considerations

- Preserve first RSVP timestamp (do not overwrite)
- External hosting for RSVP endpoint
- Email delivery tracking and retry
- Waitlist UI
- Automated scheduling trigger after RSVP cutoff

---

## Domain Gaps Before Schema

- Course contacts
- Dated course fee schedules
- Member suspensions
- Scheduling eligibility
- Outing snapshots

---

## Current Implementation Status

### Completed Recently

- RSVP email token flow works:
  - member clicks RSVP link
  - RSVP status becomes `yes`
  - original `responded_at` timestamp is preserved on repeat clicks

- Cancellation email endpoint exists:
  - `/rsvp/cancel?token=...`
  - validates token
  - removes scheduled member from outing
  - updates RSVP status from `yes` to `invited`
  - records note: `Cancelled via email link`

- Waitlist auto-promotion works:
  - when cancellation creates an open slot
  - next waitlisted player is promoted automatically
  - waitlist is based on RSVP `responded_at` order

- Schedule editor supports:
  - manual player removal
  - optional waitlist promotion
  - reduced popup friction
  - ordered waitlist display

- Test email mode improved:
  - member identity appears in email subject
  - member identity appears in email body
  - useful when all test emails route to admin/developer inbox

- Guest-aware waitlist promotion works:
  - cancellation refills vacated tee time
  - promotion respects expanded sponsor+guest capacity
  - prevents accidental fivesomes

- Fixture-backed scheduler integration tests exist:
  - temporary SQLite database
  - real schema/bootstrap path
  - guest-aware scheduling capacity checks
  - waitlist auto-promotion overflow protection

### Next Planned Work

1. Fix email delivery reliability and recipient accounting
2. Add cancellation links to pairings and revised pairings email templates
3. Trigger existing cancellation endpoint from those links
4. Refine auto-promotion logic:
   - respect guests/scheduling units
   - do not skip first waitlisted unit automatically
   - leave slot open if first waitlisted unit does not fit
5. Add audit logging:
   - who cancelled
   - when they cancelled
   - cancellation source: email link / admin
   - who was auto-promoted, if applicable
6. Refine scheduling-unit fairness:
   - sponsors + guests remain atomic requests
   - sponsors are not scheduled without confirmed guests
   - oversized units may be waitlisted while smaller later requests still fit

### Important Design Decisions

- RSVP statuses are intentionally simple:
  - `invited`
  - `yes`
- `selected`, `no`, and `maybe` are not part of the desired workflow
- Invitation targeting is eligibility-driven, not manually staged
- Non-response means not playing
- Waitlist is derived, not stored:
  - RSVP status = `yes`
  - member is not assigned to a tee time
- Admin tools should guide waitlist order but not strictly prevent override

---

## Schedule Editor Expectations

### Available Members Panel

The Available Members panel must clearly indicate sponsor-linked guests.

Examples:

- Larry Adams (+2)
- Larry Adams (+2 guests)

Preferred UI:

- sponsor displayed as expandable/collapsible node
- guests displayed beneath sponsor

Example:

Larry Adams (+2)
  ↳ Guest One
  ↳ Guest Two

### Scheduling Behavior

- Sponsors and guests should move together during scheduling operations
- Manual reassignment must preserve sponsor-guest grouping
- Capacity validation must include guests

---

## Guest Placement Philosophy

### Goals

- maximize member participation
- preserve sponsor/guest association
- avoid fivesomes
- preserve foursomes where possible
- place guest groups later in the tee sheet

### Preferred Outcome

Earlier tee times:

- primarily member-only groups

Later tee times:

- guest-containing groups
- partially filled sponsor groups

### Operational Philosophy

Members are the primary participants of the outing.

Guests are optional dependent additions that fill remaining operational capacity.

---

# Golf Club App — Domain Notes Update

## Version: v0.15-communication-workflow

### Major Architectural Evolution

The application has now evolved beyond a simple RSVP/scheduler utility into a more complete operational workflow platform with:

- workflow visibility
- communication auditing
- facility contact management
- audience-aware communication workflows
- draft-based email operations
- activity logging
- recipient previews and confirmation flows

---

# Communication Workflow Architecture

## New Dialogs

### SendCommunicationDialog

Introduced a unified communication workflow dialog.

Purpose:

- separate communication operations from RSVP management
- unify member and facility-contact communications
- provide recipient visibility before sending
- support future communication workflow expansion

Current Capabilities:

- audience selection
- template selection
- recipient previews
- draft previews
- draft editing integration
- preview/confirmation workflow
- recipient deselection preparation

---

### SendConfirmationDialog

Introduced preview/confirmation workflow dialog.

Purpose:

- final operational verification before send
- recipient visibility
- recipient deselection
- rendered email preview

Current Capabilities:

- recipient checklist
- subject preview
- body preview
- recipient confirmation

Planned Evolution:

- actual send execution
- attachment preview
- HTML rendering preview
- test mode indicators
- selective recipient persistence

---

### ActivityLogDialog

Extracted recent workflow activity from the RSVP dashboard into a dedicated dialog.

Purpose:

- reduce dashboard clutter
- preserve workflow audit visibility
- improve operational readability

Current Capabilities:

- recent workflow activity display
- email send audit visibility
- workflow event visibility

---

# Communication UX Direction

## Architectural Shift

The application is transitioning from:

```text
RSVP-centric workflow

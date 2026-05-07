# Golf Club Domain Notes (v2)

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
- Repeated clicks should not overwrite original timestamp (future refinement)

---

## RSVP Priority & Waitlist

### Status: ACTIVE (no longer future)

### Rules

- Scheduling priority is determined by RSVP "Yes" timestamp
- First-come-first-served ordering
- Sponsor-linked units inherit sponsor timestamp

### Capacity Handling

- If RSVP demand exceeds capacity:
  - earliest units are scheduled
  - remaining units go to waitlist

### Waitlist Behavior

- Ordered by RSVP timestamp
- When a cancellation occurs:
  - earliest waitlisted unit is promoted

---

## Guests

- Guests are tied to a sponsoring member
- A member may bring multiple guests

### Critical Constraint

Guests MUST be scheduled with their sponsoring member

### Scheduling Model

- Sponsor + guests = single **Scheduling Unit**
- Unit size impacts tee-time placement

---

## Scheduling Philosophy

- Prefer foursomes
- Use threesomes only when necessary
- Place threesomes in earliest tee times
- Minimize repeat pairings
- Balance tee-time fairness over time

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

## Scheduling Units (NEW)

### Definition

A Scheduling Unit is:

- sponsor member
- plus all associated guests

### Rules

- Units must not be split across tee times
- Unit size affects:
  - capacity checks
  - reshuffle logic
  - scoring

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

### Next Planned Work

1. Add cancellation links to pairings and revised pairings email templates
2. Trigger existing cancellation endpoint from those links
3. Refine auto-promotion logic:
   - respect guests/scheduling units
   - do not skip first waitlisted unit automatically
   - leave slot open if first waitlisted unit does not fit
4. Add audit logging:
   - who cancelled
   - when they cancelled
   - cancellation source: email link / admin
   - who was auto-promoted, if applicable

### Important Design Decisions

- RSVP statuses are intentionally simple:
  - `selected`
  - `invited`
  - `yes`
- `no` and `maybe` are not part of the desired workflow
- Non-response means not playing
- Waitlist is derived, not stored:
  - RSVP status = `yes`
  - member is not assigned to a tee time
- Admin tools should guide waitlist order but not strictly prevent override

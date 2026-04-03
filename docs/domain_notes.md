# Golf Club Domain Notes

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

### System Design

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

1. Outing created
2. Invitations sent (~1 week before, 5 PM)
3. Members respond (yes/no/maybe)
4. Only "yes" players are schedulable

---

## Guests

- Guests are tied to a sponsoring member
- A member may bring multiple guests

### Critical Constraint

Guests MUST be scheduled with their sponsoring member

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

## RSVP Priority & Waitlist (Future Requirement)

### Summary

Scheduling priority is determined by the timestamp of RSVP "Yes" responses.

### Rules

- Each RSVP "Yes" response must be timestamped.
- Scheduling is first-come-first-serve based on that timestamp.
- Sponsor-linked units (member + guests) are treated as a single schedulable unit.
- Units are ordered by the sponsor’s "Yes" timestamp.

### Capacity Handling

- If total RSVP-Yes units exceed tee-time capacity:
  - The earliest units are scheduled.
  - Remaining units are placed on a waitlist.

### Waitlist Behavior

- Waitlist is ordered by RSVP "Yes" timestamp.
- When a scheduled player cancels:
  - The earliest waitlisted unit is promoted into the schedule.

### UI Implications

- Edit Schedule dialog should display:
  - RSVP-Yes eligible members only
  - RSVP timestamp (e.g. "Yes at 2026-04-02 09:14")
- Waitlisted members should be visible and ordered by timestamp.

### Notes

- RSVP timestamp should reflect when status changed to "Yes".
- Future email-based RSVP system must preserve accurate timestamps.

# Backlog

---

## RSVP / Workflow

### Simplify RSVP State Model

- [x] Simplify RSVP/member participation statuses to:
  - `invited`
  - `yes`
- [x] Remove active use of:
  - `selected`
  - `no`
  - `maybe`
- [x] Rules:
  - eligible active members receive invitations unless excluded by eligibility rules
  - `invited` → invitation sent / pending response
  - `yes` → confirmed playing
  - non-response means not participating
- [x] Update:
  - database constraint (`outing_rsvps.status`)
  - repository validation
  - RSVP link handling
  - UI labels
  - workflow summary alignment

### Fix RSVP Token Flow

- [x] Restore/use `record_yes_if_first`
- [x] Ensure email RSVP links correctly mark member as `yes`
- [x] Ensure RSVP link clicks create rows if none exist
- [x] Maintain correct waitlist ordering based on original `responded_at`

### Disable Manual Member Movement

- [x] Disable double-click from Active → Invited pane
- [ ] Ensure invitation list is controlled by workflow, not manual UI

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

- [x] Do not introduce `selected` state
- [x] Confirm workflow is eligibility-driven, not manually staged
- [ ] Rename/clarify UI where needed:
  - "Invited / Confirmed Members" pane

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
  - Invited / Confirmed (right pane)
- [ ] Prevent duplicate conceptual states
- [ ] Improve visual feedback for:
  - invited vs confirmed
- [ ] Ensure members do not appear in both panes incorrectly

### Outing Status Field Review

- [ ] Evaluate usefulness of outing status:
  - draft / published / completed / cancelled
- [ ] Consider future use for online/member-facing version
- [ ] Possibly hide or simplify for current workflow

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

### Active Development Database

- Active database: `data/golf_club.db`
- Restart the RSVP server after RSVP/link-handling code changes

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

---

## Email / Communication

### Fix Email Delivery Reliability — NEXT PRIORITY

- [ ] Investigate high failure rate in email sending (e.g., 76 sent / 26 failed)
- [ ] Log detailed failure reasons per email
- [ ] Validate email addresses before sending
- [ ] Consider retry mechanism for failed sends

### Update Email Templates

- [ ] Standardize date format to `M/D/YYYY`
- [ ] Create improved default templates preferred by admins
- [ ] Allow admins to create and save custom templates

### Add General Purpose Email Template

- [ ] Add template type: `other`
- [ ] Allow sending emails unrelated to outings (e.g., events, gatherings)

### Review Test Email Feature

- [ ] Remove OR move behind admin setting
- [ ] Keep available for debugging if needed

---

## Templates / Admin Tools

### Template Management

- [ ] Allow creation of new templates
- [ ] Allow saving templates for reuse
- [ ] Support admin customization

---

### Improve Outing Workflow UI

- [ ] Move Generate Schedule out of Communication Status area
- [ ] Add clearer workflow/action area for outing steps
- [ ] Show next recommended action prominently
- [ ] Reduce reliance on admin knowing where each action lives

### Scheduler Capacity Overflow

- [ ] If confirmed players exceed capacity, schedule up to capacity
- [ ] Place remaining confirmed players on waitlist
- [ ] Do not fail schedule generation solely because demand exceeds available tee-time capacity
- [ ] Show summary:
  - confirmed players
  - scheduled players
  - waitlisted players
  - open slots

### Scheduler Constraint Relaxation

- [ ] If balanced/conservative tier constraints prevent a valid schedule, fall back gracefully
- [ ] Prefer a valid schedule over strict tier optimization
- [ ] Surface warning instead of hard failure when constraints are relaxed

---

## UI / Workflow Redesign

### Remove Generate Schedule from Manage RSVP Dialog

- [ ] Remove or hide Generate Schedule button from Manage RSVP dialog
- [ ] Treat schedule generation as an outing/scheduling action, not a communication action
- [ ] Keep “Send Pairings Email” as the communication event

### Rename Outings / Schedules Tab

- [ ] Rename tab from `Outings / Schedules` to `Outings`

### Replace Bottom Schedule List with Full Schedule Editor View

- [ ] Replace current bottom assignments list with editable schedule grid
- [ ] Reuse functionality from Edit Schedule dialog
- [ ] Consider eliminating Edit Schedule dialog after functionality is embedded

### Add Guests Main Tab

- [x] Add top-level `Guests` tab
- [x] Include buttons:
  - Add Guest
  - Edit Guest
  - Delete Guest
- [ ] Move guest management out of Manage RSVP dialog

### Add Course Contacts Management

- [x] Add Course Contacts management UI
- [ ] Consider either:
  - standalone `Course Contacts` tab
  - or unified People model

### Explore Unified People Model

- [ ] Consider single people table/entity
- [ ] Differentiate people by type:
  - Member
  - Guest
  - Course Contact
- [ ] Evaluate impacts on:
  - members
  - guests
  - course contacts
  - email recipients
  - scheduling eligibility

### Main Window Workflow Stage Panel

- [ ] Add workflow/progress panel above tabs
- [ ] Show selected outing’s current workflow stage
- [ ] Use visual stage indicators/icons
- [ ] Dim completed stages or show progress clearly
- [ ] Consider larger default main window size

### Cancellation Token Flow

- [ ] Add cancellation token/link to pairings and revised pairings email templates
- [ ] Allow scheduled member to cancel from email link
- [ ] Cancellation should:
  - remove member from schedule
  - preserve audit/history
  - trigger schedule update workflow
- [ ] If waitlist exists:
  - promote next eligible waitlisted member
- [ ] If no waitlist exists:
  - show open slot
- [ ] Define rules for late cancellations and suspensions later

### Email Token Link Presentation

- [ ] Hide raw RSVP/cancel tokens behind readable link text or buttons
- [ ] Suggested RSVP link text:
  - `Yes, I would like to play`
  - `Include me`
- [ ] Suggested cancellation link text:
  - `I need to cancel`
- [ ] Support button-style links in HTML email templates
- [ ] Keep plain-text fallback links for email clients that block HTML

### RSVP State: Cancellation Handling

- [ ] Add `cancelled` RSVP state
- [ ] When member is removed from schedule:
  - do NOT place on waitlist
  - mark as `cancelled`
- [ ] Ensure cancelled members are excluded from:
  - waitlist
  - auto-promotion logic
  - scheduling

### Waitlist Integrity

- [ ] Waitlist should only include:
  - RSVP = yes
  - not scheduled
  - not cancelled
- [ ] Do not treat all unassigned members as waitlist

---

### Open Slot Claim Validation

- [ ] Ensure all eligible members are marked as invited before allowing open-slot claim
- [ ] Fix mismatch between:
  - email distribution
  - RSVP invitation state
- [ ] Optionally relax rule:
  - allow claim if member is active and not already scheduled

---

### Distribution List Control

- [ ] Ensure all active, non-suspended members receive emails
- [ ] Add member flag:
  - `exclude_from_emails` (seasonal / temporary)
- [ ] Use this flag to control distribution list

---

### Email Delivery Reliability (Follow-up)

- [ ] Track which members actually received email
- [ ] Log delivery failures per member
- [ ] Retry failed deliveries

---

### Cancellation Token Workflow

- [ ] Add cancellation token/link to email templates (pairings and revised pairings)
- [ ] Allow members to cancel participation via email link
- [ ] On cancellation:
  - remove member from schedule
  - prevent member from being placed on waitlist
  - record cancellation event

- [ ] Introduce RSVP status: `cancelled`
  - update schema to allow: `invited`, `yes`, `cancelled`
  - ensure cancelled members are excluded from:
    - scheduling
    - waitlist
    - auto-promotion logic

- [ ] Differentiate cancellation source:
  - Admin removal → note: "Removed from schedule by admin"
  - Member cancellation → note: "Cancelled by member via email link"

- [ ] Schedule behavior after cancellation:
  - if waitlist exists → promote next eligible member
  - if no waitlist → create open slot

- [ ] UI updates:
  - display "Cancelled" as a schedule state
  - clearly distinguish from waitlist and confirmed states

- [ ] Email UX:
  - replace raw token links with readable actions:
    - "Yes, I would like to play"
    - "I need to cancel"
  - support both HTML button-style links and plain-text fallback

---

### Waitlist Promotion Workflow

- [ ] Provide a clear admin workflow for promoting waitlisted players into open schedule slots
- [ ] Preserve waitlist priority order based on original RSVP `responded_at`
- [ ] Show waitlist rank anywhere waitlisted players are displayed
- [ ] In Schedule Editor:
  - show available waitlisted players in waitlist order
  - display waitlist position beside each player
  - visually distinguish waitlisted players from other available members
- [ ] In Manage RSVP dialog:
  - consider adding action to promote selected waitlisted member into an open slot
  - only enable when open schedule slots exist
- [ ] Prevent admins from accidentally skipping waitlist order without confirmation
- [ ] If admin selects a lower-ranked waitlisted player first:
  - show warning/confirmation
  - allow override with note

  ---

### Prevent Accidental Schedule Regeneration

- [ ] Detect when an outing already has tee time assignments
- [ ] Warn admin before regenerating schedule
- [ ] Default confirmation button should be `No`
- [ ] Message should explain that regenerating replaces existing tee time assignments
- [ ] Consider separate actions:
  - Generate Schedule
  - Regenerate Schedule

  ---

### Remove Deprecated Dialogs

- [ ] Remove OutingAssignmentDialog
- [ ] Remove related references and imports
- [ ] Confirm no remaining dependencies before deletion

---

### Form Required Fields and Validation UX

- [ ] Clearly mark required fields with an asterisk (`*`)
- [ ] Add helper text to forms:
  - `* indicates required fields`
- [ ] Review Add/Edit forms for required fields:
  - Members
  - Guests
  - Courses
  - Outings
  - Course Contacts
- [ ] Require minimum fields:
  - Course: at least course name
  - Outing: at least course, outing date, tee time count
- [ ] Improve validation messages:
  - explain which fields are missing
  - focus first missing/invalid field where possible
- [ ] Consider inline validation/highlighting for missing required fields

---

---

## Recent System Updates (Post-v2 Refinement)

### RSVP State Model (Updated)

RSVP statuses have been simplified:

- invited
- yes

Notes:

- `selected`, `maybe`, and `no` are not used
- Eligible active members receive invitations unless excluded by rules
- Members are either invited, confirmed playing (`yes`), or not participating by non-response
- Admin removals revert status from `yes` → `invited` with audit note
- RSVP email-link YES clicks use `record_yes_if_first()` and create RSVP rows if missing

---

### Schedule Removal Behavior (NEW)

When an admin removes a player from the schedule:

- Player is removed from tee_time_assignments
- RSVP status is updated:
  - from "yes" → "invited"
- A note is recorded:
  - "Removed from schedule by admin"

Important:

- Removed players MUST NOT be placed on the waitlist
- Waitlist is derived only from:
  - RSVP = "yes"
  - not currently scheduled

---

### Waitlist Definition (Clarified)

Waitlist is not a stored state — it is derived:

A member is considered waitlisted if:

- RSVP status = "yes"
- not assigned to a tee time
- not removed/cancelled

Ordering:

- Based on RSVP `responded_at` timestamp (ascending)

---

### Schedule Regeneration Safety (NEW)

If a schedule already exists:

- System prompts before regenerating
- Regeneration will overwrite all existing assignments

Purpose:

- Prevent accidental loss of manual edits

---

### Messaging System (NEW)

All UI messaging is now centralized:

- show_warning()
- show_info()
- show_error()

Benefits:

- Consistent messaging across application
- Easier future improvements (logging, formatting, localization)

---

### Message Design Standard

All messages follow:

- Title: short, descriptive
- Body:
  - what happened
  - what the admin should do next

Example:

Title: Schedule Not Generated  
Body: The schedule could not be generated. Check that the outing has tee times and confirmed players, then try again.

---

### Form UX Improvements (NEW)

- Required fields are marked with `*`
- Forms guide users before validation errors occur

Future:

- Inline validation
- Highlight missing fields
- Focus first invalid field

---

### UI Workflow Clarification

Separation of responsibilities:

- Manage RSVP dialog:
  - invitations
  - RSVP tracking
  - communication workflow

- Schedule Editor:
  - tee time assignments
  - reshuffling
  - manual adjustments

- Main Window:
  - schedule generation
  - high-level workflow control

---

### Known Gaps (Active Backlog)

- Cancellation via email token
- Waitlist promotion UI
- Distribution list controls (seasonal exclusions)
- Email delivery reliability tracking
- Unified people model (members / guests / contacts)

---

### Rename Schedule Validation Warning Helper

- [ ] Rename `_warn_if_schedule_invalid_after_guest_change`
- [ ] Use a more general name such as `_warn_if_schedule_needs_review`
- [ ] Ensure RSVP, guest, and schedule changes use context-appropriate messages

---

### Email Test Mode Recipient Identification

- [ ] In preview/test email mode, include clear recipient identity in each email body
- [ ] Show:
  - member name
  - original member email
  - token/action type
- [ ] Make it easy for admins/developers to identify which token belongs to which member
- [ ] Keep this metadata out of production emails unless explicitly enabled

---

## Guest RSVP Support

Sponsors need a way to declare guests during RSVP.

Recommended approach:

- Update RSVP web page to show guest fields after sponsor clicks “Yes”
- Allow sponsor to enter guest names before confirmation
- Store guests in current schema using `guests` + `outing_guests`
- Treat sponsor + guests as an atomic scheduling group later
- Add admin visibility/editing for guest counts and names
- Add validation: max guests per sponsor, configurable per outing

---

## Auto-fill open slots after late RSVP YES

When a member clicks an RSVP YES link after a schedule has already been generated:

- If an open tee-time slot exists, automatically promote the earliest unassigned RSVP YES member.
- Respect guest-aware capacity.
- Prefer the earliest true open slot by tee-time order.
- Do not create fivesomes.
- If no valid slot exists, leave member on waitlist.
- Show clear confirmation:
  - "You have been added to the schedule"
  - or "You are on the waitlist"

---

### Guest Submission During Invitation RSVP

- [ ] Define how guests submitted during RSVP should flow into the system
- [ ] Determine whether RSVP-submitted guests should:
  - create new `guests` records automatically
  - match existing `guests` records when possible
  - require admin review before becoming official records
- [ ] Define matching rules for submitted guests:
  - first name
  - last name
  - email, if provided
  - sponsoring member
- [ ] Define how submitted guests are associated with:
  - `guests`
  - `outing_guests`
  - sponsoring member
  - outing
- [ ] Prevent duplicate guest records when the same guest plays multiple times
- [ ] Add admin review workflow for uncertain guest matches
- [ ] Ensure guest submission preserves scheduling rules:
  - guests remain attached to sponsor
  - guests do not displace members
  - guests do not independently affect RSVP priority
- [ ] Long-term Django/member portal vision:
  - members can log in
  - members can maintain their profile
  - members can manage reusable guest records
  - members can attach existing guests to an outing signup
  - members can add a new guest during outing signup
  - admin can review/edit guest records

---

### List View Sorting and Filtering

- [ ] Add sorting to major list views:
  - Facilities
  - Courses
  - Members
  - Outings
  - Guests
- [ ] Add filtering/search controls to list views
- [ ] Allow filtering Courses by Facility
- [ ] Preserve selected row after refresh where possible

# ⛳ Golf Club Management App

## Overview

A modular Python desktop application for managing a community golf club. The system handles member management, course management, outing scheduling, and tee-time assignments with a modern PyQt5 GUI and SQLite database.

---

## 🧱 Architecture

* **Language:** Python
* **UI Framework:** PyQt5
* **Database:** SQLite
* **Design Pattern:** Repository + Service Layer

### Structure

```
UI → Services → Repositories → Database
```

* **UI Layer:** Handles user interaction (forms, tables, dialogs)
* **Service Layer:** Business logic and orchestration
* **Repository Layer:** Direct database access
* **Database:** SQLite (local file-based)

---

## ⚙️ Core Features

### Members

* CRUD operations
* CSV import with validation
* Fields:

  * First Name, Last Name
  * Email, Phone
  * Handicap (optional)
  * Skill Tier (1–3)
  * Active flag (Yes/No)
  * Joined Date, Notes
* Active members only are eligible for scheduling

### Courses

* CRUD operations
* Contact info and preferred export format

### Outings (Schedules)

* Create/edit outings
* Configurable:

  * Date
  * Course
  * Start time (default 10:00 AM)
  * Tee interval (default 9 min)
  * Number of tee times
  * Players per group

### Scheduling

* Assign players to tee times
* Drag-and-drop editing
* Multi-select add/remove players
* Supports:

  * Foursomes (preferred)
  * Threesomes (when required)

### Assignments UI

* Grouped by tee time
* Clean display (no IDs)
* Column formatting and alignment
* Auto-refresh after schedule changes

### Export / Distribution

* CSV export for golf course systems
* PDF generation (basic)
* Email system (disabled during development)

---

## 🧠 Current Enhancements

### Skill Tier System

* Tier I (best), Tier II (middle), Tier III (developing)
* Constraint:

  * Tier I and Tier III should NOT be grouped together

### Active Member Logic

* Members can be toggled active/inactive
* Only active members:

  * appear in scheduling
  * can be assigned to outings

---

## 🔄 Scheduling Engine (In Progress)

### Reshuffle Feature

A "Reshuffle Schedule" button will:

* Use currently assigned players
* Rebuild groups dynamically
* Support 3- and 4-player groups
* Enforce tier constraints
* Allow repeated reshuffling

### Planned Improvements

* Avoid repeat pairings across outings
* Rotate players through tee time positions
* Introduce soft constraint fallback logic

---

## 🚧 Future Features

### RSVP System

* Members opt-in to outings
* Admin selects from RSVP list
* Automates player selection

### Suspension System

* Temporarily disable members from scheduling
* Fields:

  * suspended_until
  * suspension_reason

### Web App (Future Phase)

* Potential Django-based system
* Member self-service:

  * Registration
  * RSVP
  * Stats

---

## 🧪 Development Notes

* Email sending disabled during development
* SQLite schema evolves incrementally
* CSV import supports partial data with validation
* Git workflow uses feature branches (`feat/...`)

---

## 🚀 Current Focus

Implementing and refining:

👉 **Reshuffle Scheduling Algorithm**

Goals:

* Balanced group generation
* Tier-aware constraints
* Repeatable reshuffling
* Clean UI integration

---

## 🧭 How to Continue in a New Chat

Paste this README and say:

> “Continue implementing the reshuffle scheduling algorithm”

Then provide:

* `SchedulingService`
* `OutingRepository`
* `ScheduleEditorDialog` (if needed)

---

## 💡 Philosophy

Build iteratively:

1. Get it working
2. Make it correct
3. Make it smart
4. Make it elegant

---

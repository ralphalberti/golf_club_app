# Community Golf Club Manager

A modular Python desktop starter application for managing a community golf club.

## Features in this starter

- PyQt5 desktop GUI
- SQLite storage
- Member, course, outing, and user management
- Schedule generation with:
  - pairing-avoidance weighting
  - tee-order fairness rotation
- Editable schedules
- Round history recording
- CSV export for golf course staff
- PDF export (with a ReportLab fallback)
- Email distribution via SMTP
- Role-aware login (admin/member)

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

## Default login

If the database is empty, the app seeds:

- Username: `admin`
- Password: `admin123`

Change this immediately in a real deployment.

## Notes

- SQLite is configured with WAL mode for better multi-user behavior.
- This is a starter codebase with an intentionally clean architecture so you can evolve it.
- PDF generation uses ReportLab if installed. If ReportLab is unavailable, the app writes a text-based `.pdf.txt` fallback so the workflow still works.

## Suggested next steps

1. Replace the simple password hashing with bcrypt/argon2.
2. Add RSVP workflow and availability windows.
3. Add a drag/drop tee-sheet editor.
4. Add schedule diffing and “updated schedule” highlighting.
5. Move to PostgreSQL if concurrency requirements grow.

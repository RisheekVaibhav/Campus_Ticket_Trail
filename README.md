# Student Support & Administrative Ticket Management System

A working Django application for managing student administrative requests (fees, attendance, ID cards, documents, certificates, other) through a full ticket lifecycle: submission, deadline-aware priority calculation, department routing, staff processing, and resolution.

## Stack

Django (server-rendered templates, not a separate API), PostgreSQL, Bootstrap 5 (via CDN). No React/frontend build step is needed; the application is kept in one Django codebase. See `design_note.md` for the architecture notes.

## Setup

```
python -m venv venv
venv\Scripts\activate          (Windows)
pip install -r requirements.txt
```

Create a PostgreSQL database:
```sql
CREATE DATABASE ticket_system_db;
```

Create `.env` in the project root (see `.env.example`):
```
SECRET_KEY=your-secret-key-here
DEBUG=True
DB_NAME=ticket_system_db
DB_USER=postgres
DB_PASSWORD=your-actual-password
DB_HOST=localhost
DB_PORT=5432
```

Run migrations:
```
python manage.py migrate
```

Load sample data (users, deadline configs, sample tickets):
```
python manage.py shell -c "exec(open('seed.py', encoding='utf-8').read())"
```

Run the server:
```
python manage.py runserver
```

## Sample Login Accounts

All seeded with password: `Passw0rd!`

| Email | Role |
|---|---|
| student1@campus.edu | Student |
| student2@campus.edu | Student |
| staff_fees@campus.edu | Staff — Fees |
| staff_attendance@campus.edu | Staff — Attendance |
| staff_idcard@campus.edu | Staff — ID Card |
| staff_docs@campus.edu | Staff — Documents |
| staff_certs@campus.edu | Staff — Certificates |
| head@campus.edu | Head of Administration (also Django admin superuser) |

Django admin (for configuring deadlines): `/admin/`, login with `head@campus.edu`.

## Core Workflow

```
Student raises ticket → auto-categorized → priority computed (deadline-aware)
  → auto-routed to matching department → staff claims → staff processes
  → (optional: request more info ⟷ student responds) → staff resolves or declines
```

No separate approval step — staff can resolve or decline directly, while the Head of Administration provides oversight (see `design_note.md`).

## Priority Engine

Priority (P0–P3) is **computed, not manually chosen**, and is re-evaluated every time an open ticket is viewed or listed — so it rises automatically as a configured deadline approaches, without needing a background scheduler.

- **Fees / Attendance**: priority derives from an admin-configured official deadline (`DeadlineConfig`, managed via Django Admin) and how many days remain.
- **Documents / Certificates / ID Card / Other**: fixed baseline priority (P2), since there's no institution-wide deadline for these.
- **Manual override**: staff/Head can override priority directly, with a mandatory logged reason. Once overridden, automatic recalculation stops for that ticket.

Thresholds (`p0_days`, `p1_days`, `p2_days`) are configurable per category via Django Admin, not hard-coded.

## Roles

- **Student** — creates tickets, views own tickets only, responds to more-info requests
- **Staff** — scoped to their department, claims unclaimed tickets, processes (more info / resolve / decline), adds internal notes
- **Head of Administration** — sees everything, can reassign tickets, override priority, view staff workload and overdue (P0) tickets

## Known Limitations (see `design_note.md` for full discussion)

- No file attachment uploads
- No visual chart/analytics widgets (counts and tables instead)
- No two-step Head-of-Administration approval gate; staff resolves or declines directly
- No email notifications (in-app notification list only)
- Search/filter uses simple dropdowns, not a fully combinable query builder

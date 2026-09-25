# Design Notes — Student Support & Ticket Management System

## Overview

Students can raise requests for fees, attendance, ID cards, documents, certificates, or other administrative needs. These categories do not all have the same urgency. For example, a fee request close to a payment deadline needs faster attention than a routine ID card request. The system therefore calculates priority from the category and relevant deadline instead of asking students to choose it.

## Architecture

Server-rendered Django (templates + forms + sessions), not a separate DRF API and frontend framework. The system has several distinct screens, but it does not need to expose a public API. Keeping the application in Django gives us session-based authentication, built-in forms, and shared templates in one codebase.

## Core Entities

- **User** (custom model) — `role` (student/staff/head), `department` (staff only)
- **Ticket** — category, subject, three separate free-text fields (what needs to be done / problem description / submission details) rather than one blob, auto-generated `ticket_number`, `priority` + `priority_reason`, `status`, `department` (auto-derived from category), `assigned_to`
- **DeadlineConfig** — admin-configurable official deadline + priority-band thresholds per category
- **ActivityLog** — one row per meaningful event on a ticket (creation, categorization, priority changes, claims, requests, resolution) — this is the audit trail / timeline
- **Notification** — simple in-app message tied to a ticket and recipient

## Priority Engine

Priority is **derived, not stored as a one-time choice**. `compute_priority()` looks at the ticket's category and the relevant `DeadlineConfig` (if one exists for that category), calculates days remaining, and maps that to a P0–P3 band using admin-configurable thresholds. Documents/Certificates/ID Card/Other have no institutional deadline, so they use a fixed P2 baseline instead.

Because there is no background job or scheduler in this system, automatic escalation is handled by calling `refresh_priority()` whenever an open ticket is listed or viewed. If the computed priority differs from the stored one, it is updated and logged with a reason (for example, "Priority automatically changed from P2 to P1 because the deadline is 10 days away"). This keeps the displayed priority current without adding cron or Celery.

Staff/Head can manually override priority; once overridden, `refresh_priority()` stops recalculating that ticket automatically, since a human judgment call shouldn't be silently reverted by the deterministic engine.

## Configuration Notes

- Exact day-thresholds for P0/P1/P2/P3 bands are configurable defaults (7/14/30 days), not fixed in code — admins can adjust these per category via Django Admin. The brief asked for configurability, not specific numbers.
- Documents/Certificates default to P2 baseline (brief said "P2 or P1"); staff can manually bump to P1/P0 for genuinely urgent cases, since no deadline field exists for these categories by default.
- Department routing is 1:1 with category (Fees→Fees dept, etc.) except "Other" which routes to a "General Administration" department.

## Workflow

```
New → (staff claims, auto-moves to In Progress) → In Progress
  ⟷ More Info Needed (staff requests, student responds, returns to In Progress)
  → Resolved or Declined (terminal states, both require staff-entered detail/reason)
```

The workflow does not include a separate Head-of-Administration approval gate. Staff can resolve or decline tickets directly, while the Head role provides oversight through full ticket visibility, reassignment, and logged priority overrides.

## Cases Covered

- Student cannot view another student's ticket (403, verified in testing)
- Unauthenticated access redirects to login
- Decline and more-info-request both require a mandatory reason field (form-level validation)
- Ticket number is stable once assigned (generated after first save using the DB-assigned primary key, so no race condition on a separate counter)
- A ticket claimed by one staff member can't be silently claimed by another (checked in `claim_ticket` view)

## Current Limitations

- **Concurrent claim race**: two staff members clicking "Claim" at the exact same instant could both succeed under high concurrency, since the check-then-set isn't wrapped in a DB-level lock/transaction. Low real-world likelihood for a college-scale ticket volume, but the correct fix would be `select_for_update()` inside a transaction.
- **No file attachments**: students can describe where documents need to be submitted, but can't upload files to the ticket itself in this MVP.
- **No email delivery**: notifications are in-app only, not emailed, even though the brief's sample scenarios imply the student "receives" a message. Reasonable for a prototype; would need an email backend (e.g., Django's `send_mail` + SMTP config) to go further.

## Validation

The main workflow was checked with Django's test client across ticket creation, priority computation, department routing, staff claim, an additional-information exchange, and resolution. Permission boundaries were also checked, including student isolation and anonymous redirects.

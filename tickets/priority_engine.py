"""
Centralized priority engine.

Priority is DERIVED, not stored as a one-time choice. It is recomputed
whenever a ticket is viewed/listed (see refresh_priority below), so that
priority automatically rises as a configured deadline approaches, without
needing a background job/cron.

Fees and Attendance use an admin-configured official deadline (DeadlineConfig).
Documents / Certificates / ID Card / Other use a fixed baseline importance,
unless the student stated their own deadline, in which case that is used too.

Thresholds (p0_days / p1_days / p2_days) are configurable per category via
Django Admin (DeadlineConfig), not hard-coded - satisfies the "configurable
thresholds" requirement without a custom settings UI.
"""
from django.utils import timezone
from .models import DeadlineConfig

BASELINE_PRIORITY = {
    'documents': ('P2', 'Standard document request baseline priority.'),
    'certificates': ('P2', 'Standard certificate request baseline priority.'),
    'id_card': ('P2', 'Standard ID card request baseline priority.'),
    'fees': ('P2', 'Fee-related request; no official deadline configured yet.'),
    'attendance': ('P2', 'Attendance-related request; no official deadline configured yet.'),
    'other': ('P2', 'General administrative matter; default baseline priority.'),
}


def compute_priority(ticket):
    """Returns (priority_code, reason_string) for a given ticket, based on
    current date vs the relevant deadline (if any)."""
    today = timezone.now().date()

    config_obj = DeadlineConfig.objects.filter(category=ticket.category).first()
    deadline = None
    if config_obj and config_obj.deadline_date:
        deadline = config_obj.deadline_date
    elif ticket.student_stated_deadline:
        deadline = ticket.student_stated_deadline

    if deadline:
        days_left = (deadline - today).days
        p0 = config_obj.p0_days if config_obj else 7
        p1 = config_obj.p1_days if config_obj else 14
        p2 = config_obj.p2_days if config_obj else 30

        if days_left < 0:
            return 'P0', f"Deadline ({deadline}) has already passed ({-days_left} day(s) ago)."
        elif days_left <= p0:
            return 'P0', f"Deadline ({deadline}) is only {days_left} day(s) away."
        elif days_left <= p1:
            return 'P1', f"Deadline ({deadline}) is {days_left} days away."
        elif days_left <= p2:
            return 'P2', f"Deadline ({deadline}) is {days_left} days away."
        else:
            return 'P3', f"Deadline ({deadline}) is {days_left} days away - well in advance."

    return BASELINE_PRIORITY.get(ticket.category, ('P2', 'Default priority.'))


def refresh_priority(ticket, actor=None):
    """Recomputes and applies priority if the ticket is open and not manually
    overridden. Logs a change entry if priority actually moved. Call this
    from list/detail views for open tickets to simulate automatic escalation
    without a background scheduler."""
    from .models import ActivityLog

    if not ticket.is_open or ticket.manual_priority_override:
        return ticket

    new_priority, reason = compute_priority(ticket)
    if new_priority != ticket.priority:
        old_priority = ticket.priority
        ticket.priority = new_priority
        ticket.priority_reason = reason
        ticket.save(update_fields=['priority', 'priority_reason'])
        ActivityLog.objects.create(
            ticket=ticket,
            actor=actor,
            action=f"Priority automatically changed from {old_priority} to {new_priority}",
            detail=reason,
        )
    elif not ticket.priority_reason:
        ticket.priority_reason = reason
        ticket.save(update_fields=['priority_reason'])
    return ticket

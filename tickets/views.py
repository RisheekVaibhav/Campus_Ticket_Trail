from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseForbidden
from django.db.models import Q, Count

from .models import Ticket, ActivityLog, Notification, CATEGORY_CHOICES, STATUS_CHOICES, PRIORITY_CHOICES, OPEN_STATUSES
from .forms import (TicketCreateForm, MoreInfoRequestForm, StudentResponseForm,
                     ResolveForm, DeclineForm, InternalNoteForm, PriorityOverrideForm, ReassignForm)
from .priority_engine import compute_priority, refresh_priority


def notify(user, ticket, message):
    if user:
        Notification.objects.create(recipient=user, ticket=ticket, message=message)


# ---------- STUDENT VIEWS ----------

@login_required
def student_dashboard(request):
    if not request.user.is_student:
        return HttpResponseForbidden()
    tickets = Ticket.objects.filter(student=request.user)
    for t in tickets.filter(status__in=OPEN_STATUSES):
        refresh_priority(t)

    counts = {
        'total': tickets.count(),
        'new': tickets.filter(status='new').count(),
        'in_progress': tickets.filter(status='in_progress').count(),
        'more_info': tickets.filter(status='more_info').count(),
        'resolved': tickets.filter(status='resolved').count(),
        'declined': tickets.filter(status='declined').count(),
    }
    recent = tickets.order_by('-created_at')[:10]
    return render(request, 'tickets/student_dashboard.html', {'counts': counts, 'recent': recent})


@login_required
def create_ticket(request):
    if not request.user.is_student:
        return HttpResponseForbidden()
    if request.method == 'POST':
        form = TicketCreateForm(request.POST)
        if form.is_valid():
            ticket = form.save(commit=False)
            ticket.student = request.user
            ticket.save()
            priority, reason = compute_priority(ticket)
            ticket.priority = priority
            ticket.priority_reason = reason
            ticket.save(update_fields=['priority', 'priority_reason'])

            ActivityLog.objects.create(ticket=ticket, actor=request.user, action="Ticket created")
            ActivityLog.objects.create(ticket=ticket, actor=None,
                action=f"Automatically categorized as {ticket.get_category_display()}")
            ActivityLog.objects.create(ticket=ticket, actor=None,
                action=f"Priority assigned: {priority}", detail=reason)
            ActivityLog.objects.create(ticket=ticket, actor=None,
                action=f"Routed to {ticket.get_department_display()} queue")

            notify(request.user, ticket, f"Your ticket {ticket.ticket_number} was submitted successfully.")
            messages.success(request, f"Ticket {ticket.ticket_number} created successfully.")
            return redirect('ticket_detail', pk=ticket.pk)
    else:
        form = TicketCreateForm()
    return render(request, 'tickets/ticket_form.html', {'form': form})


@login_required
def respond_more_info(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk, student=request.user)
    if ticket.status != 'more_info':
        messages.error(request, "This ticket is not currently awaiting your response.")
        return redirect('ticket_detail', pk=pk)
    if request.method == 'POST':
        form = StudentResponseForm(request.POST)
        if form.is_valid():
            response_text = form.cleaned_data['response']
            ticket.additional_info = (ticket.additional_info + "\n\n" if ticket.additional_info else "") + \
                f"[Student response] {response_text}"
            ticket.status = 'in_progress'
            ticket.save(update_fields=['additional_info', 'status'])
            ActivityLog.objects.create(ticket=ticket, actor=request.user,
                action="Student provided additional information", detail=response_text)
            if ticket.assigned_to:
                notify(ticket.assigned_to, ticket, f"Student responded on {ticket.ticket_number}.")
            messages.success(request, "Your response was submitted.")
            return redirect('ticket_detail', pk=pk)
    else:
        form = StudentResponseForm()
    return render(request, 'tickets/respond_more_info.html', {'form': form, 'ticket': ticket})


# ---------- STAFF VIEWS ----------

@login_required
def staff_dashboard(request):
    if not request.user.is_staff_member:
        return HttpResponseForbidden()
    dept = request.user.department
    queue = Ticket.objects.filter(department=dept, status='new', assigned_to__isnull=True)
    mine = Ticket.objects.filter(assigned_to=request.user).exclude(status__in=['resolved', 'declined'])
    for t in list(queue) + list(mine):
        refresh_priority(t)

    counts = {p: mine.filter(priority=p).count() for p, _ in PRIORITY_CHOICES}
    return render(request, 'tickets/staff_dashboard.html', {
        'queue': queue.order_by('priority', '-created_at'),
        'mine': mine.order_by('priority', '-created_at'),
        'counts': counts,
    })


@login_required
def claim_ticket(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    if not request.user.is_staff_member or ticket.department != request.user.department:
        return HttpResponseForbidden()
    if ticket.assigned_to:
        messages.error(request, "This ticket is already assigned.")
        return redirect('ticket_detail', pk=pk)
    ticket.assigned_to = request.user
    ticket.status = 'in_progress'
    ticket.save(update_fields=['assigned_to', 'status'])
    ActivityLog.objects.create(ticket=ticket, actor=request.user, action=f"Claimed by {request.user.get_full_name() or request.user.username}")
    notify(ticket.student, ticket, f"Your ticket {ticket.ticket_number} is now being processed.")
    messages.success(request, "Ticket claimed.")
    return redirect('ticket_detail', pk=pk)


@login_required
def request_more_info(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    if not _can_process(request.user, ticket):
        return HttpResponseForbidden()
    if request.method == 'POST':
        form = MoreInfoRequestForm(request.POST)
        if form.is_valid():
            reason = form.cleaned_data['more_info_request']
            ticket.more_info_request = reason
            ticket.status = 'more_info'
            ticket.save(update_fields=['more_info_request', 'status'])
            ActivityLog.objects.create(ticket=ticket, actor=request.user, action="Requested additional information", detail=reason)
            notify(ticket.student, ticket, f"More information needed on {ticket.ticket_number}: {reason}")
            messages.success(request, "Requested additional information from the student.")
            return redirect('ticket_detail', pk=pk)
    else:
        form = MoreInfoRequestForm()
    return render(request, 'tickets/action_form.html', {'form': form, 'ticket': ticket, 'title': 'Request More Information'})


@login_required
def resolve_ticket(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    if not _can_process(request.user, ticket):
        return HttpResponseForbidden()
    if request.method == 'POST':
        form = ResolveForm(request.POST)
        if form.is_valid():
            details = form.cleaned_data['resolution_details']
            ticket.resolution_details = details
            ticket.status = 'resolved'
            from django.utils import timezone
            ticket.resolved_at = timezone.now()
            ticket.save(update_fields=['resolution_details', 'status', 'resolved_at'])
            ActivityLog.objects.create(ticket=ticket, actor=request.user, action="Ticket resolved", detail=details)
            notify(ticket.student, ticket, f"Your ticket {ticket.ticket_number} has been resolved: {details[:100]}")
            messages.success(request, "Ticket marked resolved.")
            return redirect('ticket_detail', pk=pk)
    else:
        form = ResolveForm()
    return render(request, 'tickets/action_form.html', {'form': form, 'ticket': ticket, 'title': 'Resolve Ticket'})


@login_required
def decline_ticket(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    if not _can_process(request.user, ticket):
        return HttpResponseForbidden()
    if request.method == 'POST':
        form = DeclineForm(request.POST)
        if form.is_valid():
            reason = form.cleaned_data['decline_reason']
            ticket.decline_reason = reason
            ticket.status = 'declined'
            from django.utils import timezone
            ticket.resolved_at = timezone.now()
            ticket.save(update_fields=['decline_reason', 'status', 'resolved_at'])
            ActivityLog.objects.create(ticket=ticket, actor=request.user, action="Ticket declined", detail=reason)
            notify(ticket.student, ticket,
                f"Your ticket {ticket.ticket_number} has been declined because: {reason} Please address this and submit a new request if needed.")
            messages.success(request, "Ticket declined.")
            return redirect('ticket_detail', pk=pk)
    else:
        form = DeclineForm()
    return render(request, 'tickets/action_form.html', {'form': form, 'ticket': ticket, 'title': 'Decline Ticket'})


@login_required
def add_note(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    if not _can_process(request.user, ticket) and not request.user.is_head:
        return HttpResponseForbidden()
    if request.method == 'POST':
        form = InternalNoteForm(request.POST)
        if form.is_valid():
            note = form.cleaned_data['note']
            ActivityLog.objects.create(ticket=ticket, actor=request.user, action="Internal note added", detail=note)
            messages.success(request, "Note added.")
    return redirect('ticket_detail', pk=pk)


def _can_process(user, ticket):
    if user.is_head:
        return True
    return user.is_staff_member and ticket.assigned_to_id == user.id


# ---------- HEAD OF ADMINISTRATION VIEWS ----------

@login_required
def head_dashboard(request):
    if not request.user.is_head:
        return HttpResponseForbidden()
    tickets = Ticket.objects.all()
    for t in tickets.filter(status__in=OPEN_STATUSES):
        refresh_priority(t)

    counts_status = {code: tickets.filter(status=code).count() for code, _ in STATUS_CHOICES}
    counts_priority = {code: tickets.filter(status__in=OPEN_STATUSES, priority=code).count() for code, _ in PRIORITY_CHOICES}
    overdue = tickets.filter(status__in=OPEN_STATUSES, priority='P0')

    from accounts.models import User
    staff_workload = User.objects.filter(role='staff').annotate(
        open_count=Count('tickets_assigned', filter=Q(tickets_assigned__status__in=OPEN_STATUSES))
    )

    return render(request, 'tickets/head_dashboard.html', {
        'counts_status': counts_status,
        'counts_priority': counts_priority,
        'overdue': overdue,
        'staff_workload': staff_workload,
        'total_open': tickets.filter(status__in=OPEN_STATUSES).count(),
    })


@login_required
def reassign_ticket(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    if not request.user.is_head:
        return HttpResponseForbidden()
    if request.method == 'POST':
        form = ReassignForm(request.POST, department=ticket.department)
        if form.is_valid():
            new_staff = form.cleaned_data['assigned_to']
            old_staff = ticket.assigned_to
            ticket.assigned_to = new_staff
            ticket.status = 'in_progress'
            ticket.save(update_fields=['assigned_to', 'status'])
            ActivityLog.objects.create(ticket=ticket, actor=request.user,
                action=f"Reassigned by Head of Administration",
                detail=f"From {old_staff or 'Unassigned'} to {new_staff}")
            notify(new_staff, ticket, f"Ticket {ticket.ticket_number} has been assigned to you.")
            messages.success(request, "Ticket reassigned.")
            return redirect('ticket_detail', pk=pk)
    else:
        form = ReassignForm(department=ticket.department)
    return render(request, 'tickets/action_form.html', {'form': form, 'ticket': ticket, 'title': 'Reassign Ticket'})


@login_required
def override_priority(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    if not request.user.is_head:
        return HttpResponseForbidden()
    if request.method == 'POST':
        form = PriorityOverrideForm(request.POST)
        if form.is_valid():
            old_priority = ticket.priority
            ticket.priority = form.cleaned_data['priority']
            ticket.priority_reason = f"Manually overridden: {form.cleaned_data['reason']}"
            ticket.manual_priority_override = True
            ticket.save(update_fields=['priority', 'priority_reason', 'manual_priority_override'])
            ActivityLog.objects.create(ticket=ticket, actor=request.user,
                action=f"Priority manually overridden from {old_priority} to {ticket.priority}",
                detail=form.cleaned_data['reason'])
            messages.success(request, "Priority overridden.")
            return redirect('ticket_detail', pk=pk)
    else:
        form = PriorityOverrideForm(initial={'priority': ticket.priority})
    return render(request, 'tickets/action_form.html', {'form': form, 'ticket': ticket, 'title': 'Override Priority'})


# ---------- SHARED ----------

@login_required
def ticket_detail(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    user = request.user
    if user.is_student and ticket.student_id != user.id:
        return HttpResponseForbidden()
    if user.is_staff_member and ticket.department != user.department:
        return HttpResponseForbidden()

    if ticket.is_open:
        refresh_priority(ticket)

    return render(request, 'tickets/ticket_detail.html', {
        'ticket': ticket,
        'activities': ticket.activities.select_related('actor').all(),
        'can_process': _can_process(user, ticket),
    })


@login_required
def ticket_list(request):
    user = request.user
    if user.is_student:
        qs = Ticket.objects.filter(student=user)
    elif user.is_staff_member:
        qs = Ticket.objects.filter(department=user.department)
    elif user.is_head:
        qs = Ticket.objects.all()
    else:
        return HttpResponseForbidden()

    status = request.GET.get('status')
    priority = request.GET.get('priority')
    category = request.GET.get('category')
    department = request.GET.get('department')
    q = request.GET.get('q')

    if status:
        qs = qs.filter(status=status)
    if priority:
        qs = qs.filter(priority=priority)
    if category:
        qs = qs.filter(category=category)
    if department and user.is_head:
        qs = qs.filter(department=department)
    if q:
        qs = qs.filter(Q(ticket_number__icontains=q) | Q(subject__icontains=q) |
                        Q(student__username__icontains=q) | Q(student__first_name__icontains=q))

    return render(request, 'tickets/ticket_list.html', {
        'tickets': qs.order_by('priority', '-created_at'),
        'status_choices': STATUS_CHOICES,
        'priority_choices': PRIORITY_CHOICES,
        'category_choices': CATEGORY_CHOICES,
    })


@login_required
def notifications_view(request):
    notes = request.user.notifications.all()
    notes.filter(is_read=False).update(is_read=True)
    return render(request, 'tickets/notifications.html', {'notes': notes})

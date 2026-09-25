from django.db import models
from django.conf import settings
from django.utils import timezone

CATEGORY_CHOICES = [
    ('fees', 'Fees'),
    ('attendance', 'Attendance'),
    ('id_card', 'ID Card'),
    ('documents', 'Documents'),
    ('certificates', 'Certificates'),
    ('other', 'Other Administrative Matter'),
]

CATEGORY_TO_DEPARTMENT = {
    'fees': 'fees',
    'attendance': 'attendance',
    'id_card': 'id_card',
    'documents': 'documents',
    'certificates': 'certificates',
    'other': 'general',
}

PRIORITY_CHOICES = [
    ('P0', 'P0 - Critical'),
    ('P1', 'P1 - High'),
    ('P2', 'P2 - Medium'),
    ('P3', 'P3 - Low'),
]
PRIORITY_ORDER = {'P0': 0, 'P1': 1, 'P2': 2, 'P3': 3}

DEPARTMENT_CHOICES = [
    ('fees', 'Fees'),
    ('attendance', 'Attendance'),
    ('id_card', 'ID Card'),
    ('documents', 'Documents'),
    ('certificates', 'Certificates'),
    ('general', 'General Administration'),
]

STATUS_CHOICES = [
    ('new', 'New'),
    ('in_progress', 'In Progress'),
    ('more_info', 'More Information Needed'),
    ('resolved', 'Resolved'),
    ('declined', 'Declined'),
]

OPEN_STATUSES = ['new', 'in_progress', 'more_info']


class DeadlineConfig(models.Model):
    """Admin-configurable official deadlines that feed the priority engine.
    Manage these from /admin/ - no custom UI needed for the MVP."""
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, unique=True)
    deadline_date = models.DateField(null=True, blank=True,
        help_text="Official institutional deadline for this category, e.g. fee due date.")
    p0_days = models.PositiveIntegerField(default=7, help_text="Days remaining at/under which priority becomes P0")
    p1_days = models.PositiveIntegerField(default=14, help_text="Days remaining at/under which priority becomes P1")
    p2_days = models.PositiveIntegerField(default=30, help_text="Days remaining at/under which priority becomes P2 (beyond this = P3)")

    def __str__(self):
        return f"{self.get_category_display()} deadline: {self.deadline_date}"

    class Meta:
        verbose_name = "Deadline Configuration"
        verbose_name_plural = "Deadline Configurations"


def generate_ticket_number(pk, created_at):
    return f"TKT-{created_at.year}-{pk:06d}"


class Ticket(models.Model):
    ticket_number = models.CharField(max_length=30, unique=True, editable=False, blank=True)

    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='tickets_raised')

    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    subject = models.CharField(max_length=255)
    what_needs_to_be_done = models.TextField()
    problem_description = models.TextField()
    submission_details = models.TextField(blank=True,
        help_text="Where documents need to be submitted, which department/person requested them, portal info, etc.")
    student_stated_deadline = models.DateField(null=True, blank=True)
    additional_info = models.TextField(blank=True)

    priority = models.CharField(max_length=2, choices=PRIORITY_CHOICES, default='P3')
    priority_reason = models.CharField(max_length=500, blank=True)
    manual_priority_override = models.BooleanField(default=False)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    department = models.CharField(max_length=20, choices=DEPARTMENT_CHOICES, blank=True)
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='tickets_assigned')

    decline_reason = models.TextField(blank=True)
    more_info_request = models.TextField(blank=True)
    resolution_details = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.ticket_number} - {self.subject}"

    def save(self, *args, **kwargs):
        if not self.department:
            self.department = CATEGORY_TO_DEPARTMENT.get(self.category, 'general')
        creating = self._state.adding
        super().save(*args, **kwargs)
        if creating and not self.ticket_number:
            self.ticket_number = generate_ticket_number(self.pk, self.created_at)
            Ticket.objects.filter(pk=self.pk).update(ticket_number=self.ticket_number)
            self.refresh_from_db(fields=['ticket_number'])

    @property
    def is_open(self):
        return self.status in OPEN_STATUSES

    @property
    def is_overdue(self):
        """A ticket is overdue if its priority is P0 and it's still open."""
        return self.is_open and self.priority == 'P0'


class ActivityLog(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='activities')
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=255)
    detail = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.ticket.ticket_number}: {self.action}"


class Notification(models.Model):
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='notifications')
    message = models.CharField(max_length=500)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"To {self.recipient}: {self.message[:40]}"

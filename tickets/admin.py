from django.contrib import admin
from .models import Ticket, ActivityLog, DeadlineConfig, Notification

@admin.register(DeadlineConfig)
class DeadlineConfigAdmin(admin.ModelAdmin):
    list_display = ('category', 'deadline_date', 'p0_days', 'p1_days', 'p2_days')

@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ('ticket_number', 'subject', 'category', 'priority', 'status', 'department', 'assigned_to', 'student')
    list_filter = ('category', 'priority', 'status', 'department')
    search_fields = ('ticket_number', 'subject')

@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ('ticket', 'actor', 'action', 'created_at')

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'ticket', 'message', 'is_read', 'created_at')

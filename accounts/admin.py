from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'role', 'department', 'is_active')
    fieldsets = UserAdmin.fieldsets + (
        ('Ticket System Role', {'fields': ('role', 'department', 'student_id')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Ticket System Role', {'fields': ('role', 'department', 'student_id', 'email')}),
    )

admin.site.register(User, CustomUserAdmin)

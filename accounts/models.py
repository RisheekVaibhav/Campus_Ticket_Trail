from django.contrib.auth.models import AbstractUser
from django.db import models

ROLE_CHOICES = [
    ('student', 'Student'),
    ('staff', 'Administrative Staff'),
    ('head', 'Head of Administration'),
]

DEPARTMENT_CHOICES = [
    ('fees', 'Fees'),
    ('attendance', 'Attendance'),
    ('id_card', 'ID Card'),
    ('documents', 'Documents'),
    ('certificates', 'Certificates'),
    ('general', 'General Administration'),
]


class User(AbstractUser):
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')
    department = models.CharField(max_length=20, choices=DEPARTMENT_CHOICES, blank=True, null=True)
    student_id = models.CharField(max_length=30, blank=True, null=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"

    @property
    def is_student(self):
        return self.role == 'student'

    @property
    def is_staff_member(self):
        return self.role == 'staff'

    @property
    def is_head(self):
        return self.role == 'head'

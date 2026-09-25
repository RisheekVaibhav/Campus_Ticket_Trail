"""
Run with: python manage.py shell -c "exec(open('seed.py', encoding='utf-8').read())"
Creates sample users, deadline configs, and tickets for local development.
"""
import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ticket_system.settings')
django.setup()

from datetime import date, timedelta
from accounts.models import User
from tickets.models import Ticket, DeadlineConfig, ActivityLog
from tickets.priority_engine import compute_priority

PASSWORD = "Passw0rd!"

def get_or_create_user(username, email, role, department=None, student_id=None, first="", last=""):
    u, created = User.objects.get_or_create(username=username, defaults={
        'email': email, 'role': role, 'department': department,
        'student_id': student_id, 'first_name': first, 'last_name': last,
    })
    if created:
        u.set_password(PASSWORD)
        u.save()
    return u

# Users
student1 = get_or_create_user('student1', 'student1@campus.edu', 'student', student_id='STU2026001', first='Aisha', last='Khan')
student2 = get_or_create_user('student2', 'student2@campus.edu', 'student', student_id='STU2026002', first='Rohan', last='Mehta')

staff_fees = get_or_create_user('staff_fees', 'staff_fees@campus.edu', 'staff', department='fees', first='Priya', last='Iyer')
staff_attendance = get_or_create_user('staff_attendance', 'staff_attendance@campus.edu', 'staff', department='attendance', first='Karan', last='Shah')
staff_idcard = get_or_create_user('staff_idcard', 'staff_idcard@campus.edu', 'staff', department='id_card', first='Neha', last='Rao')
staff_docs = get_or_create_user('staff_docs', 'staff_docs@campus.edu', 'staff', department='documents', first='Amit', last='Verma')
staff_certs = get_or_create_user('staff_certs', 'staff_certs@campus.edu', 'staff', department='certificates', first='Divya', last='Nair')

head = get_or_create_user('head_admin', 'head@campus.edu', 'head', first='Dr. Ramesh', last='Gupta')
if not head.is_staff:
    head.is_staff = True
    head.is_superuser = True
    head.save()

# Deadline configs
DeadlineConfig.objects.get_or_create(category='fees', defaults={
    'deadline_date': date.today() + timedelta(days=5), 'p0_days': 7, 'p1_days': 14, 'p2_days': 30})
DeadlineConfig.objects.get_or_create(category='attendance', defaults={
    'deadline_date': date.today() + timedelta(days=60), 'p0_days': 7, 'p1_days': 14, 'p2_days': 30})

# Sample tickets
def make_ticket(student, category, subject, needs, problem, submission="", deadline=None):
    t = Ticket(student=student, category=category, subject=subject,
               what_needs_to_be_done=needs, problem_description=problem,
               submission_details=submission, student_stated_deadline=deadline)
    t.save()
    p, reason = compute_priority(t)
    t.priority = p
    t.priority_reason = reason
    t.save(update_fields=['priority', 'priority_reason'])
    ActivityLog.objects.create(ticket=t, actor=student, action="Ticket created")
    ActivityLog.objects.create(ticket=t, actor=None, action=f"Priority assigned: {p}", detail=reason)
    return t

if not Ticket.objects.exists():
    make_ticket(student1, 'fees', 'Unable to pay semester fees',
                'Please help me complete my semester fee payment before the deadline.',
                'Payment gateway keeps failing when I try to pay via the student portal.',
                'Fees portal at portal.campus.edu/fees')

    make_ticket(student2, 'attendance', 'Attendance correction request',
                'Please correct my attendance for 12th and 13th March, I was on official college duty.',
                'My attendance shows absent on those dates despite being on a college-approved trip.',
                'Attendance office, Block A')

    make_ticket(student1, 'documents', 'Bonafide certificate request',
                'I need a bonafide certificate for a scholarship application.',
                'I could not find the correct request form on the portal.',
                'To be submitted to the scholarship portal by the student.')

    make_ticket(student2, 'certificates', 'Duplicate degree certificate',
                'I need a duplicate copy of my provisional degree certificate.',
                'My original was damaged.')

    make_ticket(student1, 'id_card', 'Lost ID card - need reissue',
                'Please issue a new student ID card.',
                'I lost my ID card last week.')

    print(f"Seeded {Ticket.objects.count()} tickets.")
else:
    print("Tickets already exist, skipping ticket seed.")

print("Seed complete.")
print("Login as: student1@campus.edu / staff_fees@campus.edu / head@campus.edu, all with password:", PASSWORD)

from django.urls import path
from . import views

urlpatterns = [
    path('student/', views.student_dashboard, name='student_dashboard'),
    path('staff/', views.staff_dashboard, name='staff_dashboard'),
    path('head/', views.head_dashboard, name='head_dashboard'),

    path('create/', views.create_ticket, name='create_ticket'),
    path('list/', views.ticket_list, name='ticket_list'),
    path('<int:pk>/', views.ticket_detail, name='ticket_detail'),
    path('<int:pk>/respond/', views.respond_more_info, name='respond_more_info'),

    path('<int:pk>/claim/', views.claim_ticket, name='claim_ticket'),
    path('<int:pk>/request-more-info/', views.request_more_info, name='request_more_info'),
    path('<int:pk>/resolve/', views.resolve_ticket, name='resolve_ticket'),
    path('<int:pk>/decline/', views.decline_ticket, name='decline_ticket'),
    path('<int:pk>/note/', views.add_note, name='add_note'),

    path('<int:pk>/reassign/', views.reassign_ticket, name='reassign_ticket'),
    path('<int:pk>/override-priority/', views.override_priority, name='override_priority'),

    path('notifications/', views.notifications_view, name='notifications'),
]

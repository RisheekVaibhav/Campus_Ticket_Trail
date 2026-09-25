from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        user = authenticate(request, username=email, password=password)
        if user:
            login(request, user)
            return redirect('dashboard')
        messages.error(request, 'Invalid email or password.')
    return render(request, 'registration/login.html')


def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def dashboard_router(request):
    """Sends each role to its own dashboard."""
    if request.user.is_student:
        return redirect('student_dashboard')
    elif request.user.is_staff_member:
        return redirect('staff_dashboard')
    elif request.user.is_head:
        return redirect('head_dashboard')
    return redirect('login')

from django.contrib import admin
from django.urls import path, include
from accounts import views as account_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', account_views.dashboard_router, name='home'),
    path('accounts/', include('accounts.urls')),
    path('tickets/', include('tickets.urls')),
]

from django.urls import path
from . import views
from django.contrib.auth.views import LogoutView

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', views.login_user, name='login'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('logout/', LogoutView.as_view(next_page='login'), name='logout'),
    path('transfer/', views.transfer, name='transfer'),
    path('deposit/', views.deposit, name='deposit'),
    path('export/', views.export_transactions, name='export_transactions'),
    path('profile/', views.profile, name='profile'),
]

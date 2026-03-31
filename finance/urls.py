from django.contrib import admin
from django.urls import path

from finance.views import (
    CustomLoginView,
    DashboardView,
    GoalCreateView,
    ProfileView,
    RegisterView,
    TransactionCreateView,
    TransactionListView,
    export_transactions,
)

urlpatterns = [
    path('accounts/login/', CustomLoginView.as_view(), name='login'),
    path('register/', RegisterView.as_view(), name='register'),
    path('', DashboardView.as_view(), name='dashboard'),
    path('transaction/add/', TransactionCreateView.as_view(), name='transaction_add'),
    path('transactions/', TransactionListView.as_view(), name='transaction_list'),
    path('goal/add/', GoalCreateView.as_view(), name='goal_add'),
    path('generate-report/', export_transactions, name='export_transactions'),
    path('profile/', ProfileView.as_view(), name='profile'),
]

from datetime import date

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.db.models import Q, Sum
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, ListView

from finance.forms import (
    AvatarUploadForm,
    BudgetForm,
    CustomLoginForm,
    GoalContributionForm,
    GoalForm,
    RegisterForm,
    TransactionForm,
)

from .admin import TransactionResource
from .models import Goal, GoalContribution, Transaction, UserProfile


class CustomLoginView(LoginView):
    form_class = CustomLoginForm
    template_name = "registration/login.html"

    def form_invalid(self, form):
        messages.error(self.request, "Not valid: username or password is not registered.")
        return super().form_invalid(form)


class RegisterView(View):
    def get(self, request, *args, **kwargs):
        form = RegisterForm()
        return render(request, "finance/register.html", {"form": form})

    def post(self, request, *args, **kwargs):
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Registration successful.")
            return redirect("dashboard")
        messages.error(request, "Registration failed. Fix the highlighted fields and try again.")
        for errors in form.errors.values():
            for error in errors:
                messages.error(request, error)
        return render(request, "finance/register.html", {"form": form})


class DashboardView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        transactions = Transaction.objects.filter(user=request.user)
        goals = Goal.objects.filter(user=request.user).prefetch_related("contributions")
        user_profile, _ = UserProfile.objects.get_or_create(user=request.user)

        total_income = transactions.filter(transaction_type="income").aggregate(
            Sum("amount")
        )["amount__sum"] or 0
        total_expenses = transactions.filter(transaction_type="expense").aggregate(
            Sum("amount")
        )["amount__sum"] or 0
        net_savings = total_income - total_expenses
        goal_progress = []

        for goal in goals:
            progress = (goal.current_amount / goal.target_amount) * 100 if goal.target_amount > 0 else 0
            goal_progress.append(
                {
                    "goal": goal,
                    "progress": min(progress, 100),
                    "history": list(goal.contributions.all()[:4]),
                }
            )

        expense_by_category = list(
            transactions.filter(transaction_type="expense")
            .values("category")
            .annotate(total=Sum("amount"))
            .order_by("-total")
        )
        category_labels = [item["category"] for item in expense_by_category]
        category_totals = [float(item["total"]) for item in expense_by_category]
        budget_alert = build_budget_alert(user_profile.monthly_budget, total_expenses)

        context = {
            "transactions": transactions,
            "goals": goals,
            "total_income": total_income,
            "total_expenses": total_expenses,
            "net_savings": net_savings,
            "goal_progress": goal_progress,
            "income_expense_labels": ["Income", "Expenses"],
            "income_expense_values": [float(total_income), float(total_expenses)],
            "category_labels": category_labels,
            "category_totals": category_totals,
            "budget_alert": budget_alert,
            "goal_count": goals.count(),
        }
        return render(request, "finance/dashboard.html", context)


class TransactionCreateView(LoginRequiredMixin, CreateView):
    model = Transaction
    form_class = TransactionForm
    template_name = "finance/transaction_form.html"
    success_url = reverse_lazy("transaction_list")

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)


class TransactionListView(LoginRequiredMixin, ListView):
    model = Transaction
    template_name = "finance/transaction_list.html"
    context_object_name = "transactions"

    def get_queryset(self):
        queryset = Transaction.objects.filter(user=self.request.user)
        query = self.request.GET.get("q")
        history_type = self.request.GET.get("history_type")
        history_period = self.request.GET.get("history_period")
        history_value = self.request.GET.get("history_value")

        if query:
            queryset = queryset.filter(
                Q(title__icontains=query)
                | Q(category__icontains=query)
                | Q(description__icontains=query)
            )

        if history_type in {"income", "expense"}:
            queryset = queryset.filter(transaction_type=history_type)

        queryset = self.apply_history_filter(queryset, history_period, history_value)
        return queryset.order_by("-date")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["search_query"] = self.request.GET.get("q", "")
        context["history_type"] = self.request.GET.get("history_type", "")
        context["history_period"] = self.request.GET.get("history_period", "")
        context["history_value"] = self.request.GET.get("history_value", "")
        return context

    def apply_history_filter(self, queryset, history_period, history_value):
        if not history_period or not history_value:
            return queryset

        try:
            if history_period == "weekly":
                year_part, week_part = history_value.split("-W")
                iso_year = int(year_part)
                iso_week = int(week_part)
                week_start = date.fromisocalendar(iso_year, iso_week, 1)
                week_end = date.fromisocalendar(iso_year, iso_week, 7)
                return queryset.filter(date__range=(week_start, week_end))

            if history_period == "monthly":
                year_part, month_part = history_value.split("-")
                return queryset.filter(
                    date__year=int(year_part),
                    date__month=int(month_part),
                )

            if history_period == "yearly":
                return queryset.filter(date__year=int(history_value))
        except (TypeError, ValueError):
            return queryset

        return queryset


class GoalCreateView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        return render(request, "finance/goal_form.html", self.get_context(request))

    def post(self, request, *args, **kwargs):
        form_type = request.POST.get("form_type")

        if form_type == "ongoing_goal":
            ongoing_form = GoalContributionForm(request.POST, user=request.user)
            if ongoing_form.is_valid():
                contribution = ongoing_form.save(commit=False)
                goal = contribution.goal
                goal.current_amount += contribution.amount
                goal.saved_on = contribution.saved_on
                goal.save(update_fields=["current_amount", "saved_on"])
                contribution.save()
                messages.success(request, "New goal record added to history.")
                return redirect("goal_add")

            return render(
                request,
                "finance/goal_form.html",
                self.get_context(request, ongoing_form=ongoing_form),
            )

        create_form = GoalForm(request.POST)
        if create_form.is_valid():
            goal = create_form.save(commit=False)
            goal.user = request.user
            goal.save()
            if goal.current_amount > 0:
                GoalContribution.objects.create(
                    goal=goal,
                    amount=goal.current_amount,
                    saved_on=goal.saved_on,
                    note="Initial saved amount",
                )
            messages.success(request, "Goal added successfully.")
            return redirect("goal_add")
        return render(request, "finance/goal_form.html", self.get_context(request, create_form=create_form))

    def get_context(self, request, create_form=None, ongoing_form=None):
        goals = Goal.objects.filter(user=request.user).prefetch_related("contributions").order_by("deadline", "title")
        goal_cards = [
            {
                "goal": goal,
                "progress": min((goal.current_amount / goal.target_amount) * 100, 100) if goal.target_amount > 0 else 0,
                "history": list(goal.contributions.all()[:5]),
            }
            for goal in goals
        ]
        return {
            "create_form": create_form or GoalForm(),
            "ongoing_form": ongoing_form or GoalContributionForm(user=request.user),
            "goal_cards": goal_cards,
        }


@login_required
def export_transactions(request):
    user_transactions = Transaction.objects.filter(user=request.user)
    transctions_resource = TransactionResource()
    dataset = transctions_resource.export(queryset=user_transactions)
    excel_data = dataset.export("xlsx")

    response = HttpResponse(
        excel_data,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = "attachment; filename=transactions_report.xlsx"
    return response


def build_budget_alert(monthly_budget, expense):
    if not monthly_budget:
        return None

    spent_percentage = float((expense / monthly_budget) * 100) if monthly_budget > 0 else 0
    alert = {
        "budget": monthly_budget,
        "expense": expense,
        "remaining": monthly_budget - expense,
        "spent_percentage": min(spent_percentage, 100) if spent_percentage > 0 else 0,
        "status": "safe",
        "title": "Budget on track",
        "message": "Your monthly spending is within a healthy range.",
    }

    if expense >= monthly_budget:
        alert.update(
            {
                "status": "danger",
                "title": "Budget exceeded",
                "message": "Your expenses have crossed the monthly budget you set.",
                "spent_percentage": 100,
            }
        )
    elif spent_percentage >= 80:
        alert.update(
            {
                "status": "warning",
                "title": "Budget warning",
                "message": "You have used more than 80% of your monthly budget.",
            }
        )

    return alert


class ProfileView(LoginRequiredMixin, View):
    def get_profile_context(self, request, avatar_form=None, budget_form=None):
        user = request.user
        today = date.today()
        user_profile, _ = UserProfile.objects.get_or_create(user=user)

        monthly_transactions = Transaction.objects.filter(
            user=user,
            date__month=today.month,
            date__year=today.year,
        )

        income = monthly_transactions.filter(transaction_type="income").aggregate(
            total=Sum("amount")
        )["total"] or 0
        expense = monthly_transactions.filter(transaction_type="expense").aggregate(
            total=Sum("amount")
        )["total"] or 0
        balance = income - expense
        budget_alert = build_budget_alert(user_profile.monthly_budget, expense)

        context = {
            "income": income,
            "expense": expense,
            "balance": balance,
            "total_transactions": monthly_transactions.count(),
            "user_profile": user_profile,
            "avatar_form": avatar_form or AvatarUploadForm(instance=user_profile),
            "budget_form": budget_form or BudgetForm(instance=user_profile),
            "budget_alert": budget_alert,
        }
        return context

    def get(self, request):
        return render(request, "finance/profile.html", self.get_profile_context(request))

    def post(self, request):
        user_profile, _ = UserProfile.objects.get_or_create(user=request.user)
        form_type = request.POST.get("form_type")

        if form_type == "budget":
            budget_form = BudgetForm(request.POST, instance=user_profile)
            if budget_form.is_valid():
                budget_form.save()
                messages.success(request, "Monthly budget updated.")
                return redirect("profile")
            return render(
                request,
                "finance/profile.html",
                self.get_profile_context(request, budget_form=budget_form),
            )

        avatar_form = AvatarUploadForm(request.POST, request.FILES, instance=user_profile)
        if avatar_form.is_valid():
            avatar_form.save()
            messages.success(request, "Profile avatar updated.")
            return redirect("profile")

        return render(
            request,
            "finance/profile.html",
            self.get_profile_context(request, avatar_form=avatar_form),
        )

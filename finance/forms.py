from datetime import date
import re

from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User

from .models import Goal, GoalContribution, Transaction, UserProfile


class CustomLoginForm(AuthenticationForm):
    error_messages = {
        **AuthenticationForm.error_messages,
        "invalid_login": "Not valid: username or password is not registered.",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'custom-input'})


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'custom-input'})

        self.fields["username"].widget.attrs["placeholder"] = "Choose a username"
        self.fields["email"].widget.attrs["placeholder"] = "Enter your email"
        self.fields["password1"].widget.attrs["placeholder"] = "Create a password"
        self.fields["password2"].widget.attrs["placeholder"] = "Confirm your password"
        self.fields["password1"].help_text = "Use at least one special character such as @, #, !, or %."

    def clean_password1(self):
        password = self.cleaned_data.get("password1", "")
        if not re.search(r"[^A-Za-z0-9]", password):
            raise forms.ValidationError("Password must include at least one special character.")
        return password


class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ["transaction_type", "date", "amount", "category"]
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control custom-input'})

        self.fields['date'].widget.attrs['min'] = date.today().isoformat()
        self.fields['amount'].widget.attrs['placeholder'] = 'Amount in INR'
        self.fields['category'].label = 'Category'
        self.fields['category'].widget.attrs['placeholder'] = 'Food, Travel, Salary, Rent'

    def clean_date(self):
        selected_date = self.cleaned_data["date"]
        if selected_date < date.today():
            raise forms.ValidationError("Please choose today or a future date.")
        return selected_date

    def save(self, commit=True):
        self.instance.title = self.cleaned_data["category"]
        self.instance.description = self.cleaned_data["category"]
        return super().save(commit=commit)


class GoalForm(forms.ModelForm):
    class Meta:
        model = Goal
        fields = ['title', 'target_amount', 'current_amount', 'started_on', 'saved_on', 'deadline']
        widgets = {
            'title': forms.TextInput(attrs={
                'placeholder': 'Example: Buy Laptop'
            }),
            'target_amount': forms.NumberInput(attrs={
                'placeholder': '50000'
            }),
            'current_amount': forms.NumberInput(attrs={
                'placeholder': '5000'
            }),
            'started_on': forms.DateInput(attrs={
                'type': 'date'
            }),
            'saved_on': forms.DateInput(attrs={
                'type': 'date'
            }),
            'deadline': forms.DateInput(attrs={
                'type': 'date'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['started_on'].widget.attrs.update({
            'type': 'date',
            'max': date.today().isoformat(),
        })
        self.fields['saved_on'].widget.attrs.update({
            'type': 'date',
            'max': date.today().isoformat(),
        })
        self.fields['deadline'].widget.attrs.update({
            'type': 'date',
            'min': date.today().isoformat(),
        })

    def clean(self):
        cleaned_data = super().clean()
        started_on = cleaned_data.get("started_on")
        saved_on = cleaned_data.get("saved_on")
        deadline = cleaned_data.get("deadline")

        if started_on and saved_on and saved_on < started_on:
            self.add_error("saved_on", "Saved date cannot be earlier than the goal start date.")

        if started_on and deadline and deadline < started_on:
            self.add_error("deadline", "Deadline cannot be earlier than the goal start date.")

        return cleaned_data


class GoalContributionForm(forms.ModelForm):
    goal = forms.ModelChoiceField(
        queryset=Goal.objects.none(),
        empty_label="Select a goal",
    )

    class Meta:
        model = GoalContribution
        fields = ["goal", "amount", "saved_on", "note"]
        widgets = {
            "amount": forms.NumberInput(attrs={"placeholder": "1500"}),
            "saved_on": forms.DateInput(attrs={"type": "date"}),
            "note": forms.TextInput(attrs={"placeholder": "Added more savings this week"}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            field.widget.attrs.update({"class": "form-control custom-input"})

        self.fields["amount"].widget.attrs.update({"min": "0.01", "step": "0.01"})
        self.fields["saved_on"].widget.attrs.update({
            "type": "date",
            "max": date.today().isoformat(),
        })

        if user is not None:
            self.fields["goal"].queryset = Goal.objects.filter(user=user).order_by("title")

    def clean_amount(self):
        amount = self.cleaned_data["amount"]
        if amount <= 0:
            raise forms.ValidationError("Contribution amount must be greater than zero.")
        return amount

    def clean(self):
        cleaned_data = super().clean()
        goal = cleaned_data.get("goal")
        saved_on = cleaned_data.get("saved_on")

        if goal and saved_on and saved_on < goal.started_on:
            self.add_error("saved_on", "Record date cannot be earlier than the goal start date.")

        return cleaned_data


class AvatarUploadForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ["avatar"]

    def clean_avatar(self):
        avatar = self.cleaned_data.get("avatar")
        if not avatar:
            return avatar

        allowed_types = {"image/jpeg", "image/png", "image/webp", "image/gif"}
        content_type = getattr(avatar, "content_type", "")
        if content_type not in allowed_types:
            raise forms.ValidationError("Upload a JPG, PNG, WEBP, or GIF image.")
        return avatar


class BudgetForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ["monthly_budget"]
        widgets = {
            "monthly_budget": forms.NumberInput(
                attrs={
                    "placeholder": "Set your monthly budget",
                    "min": "0",
                    "step": "0.01",
                }
            )
        }

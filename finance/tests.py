from datetime import date

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from .forms import RegisterForm
from .models import Transaction, UserProfile


class FinanceViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='alice',
            email='alice@example.com',
            password='testpass123',
        )
        self.client.login(username='alice', password='testpass123')

    def test_dashboard_uses_net_savings_context(self):
        Transaction.objects.create(
            user=self.user,
            title='Salary',
            amount=1000,
            transaction_type='income',
            date=date.today(),
            description='Monthly salary',
            category='Job',
        )
        Transaction.objects.create(
            user=self.user,
            title='Rent',
            amount=400,
            transaction_type='expense',
            date=date.today(),
            description='Rent payment',
            category='Housing',
        )

        response = self.client.get(reverse('dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['net_savings'], 600)

    def test_profile_route_renders_monthly_totals(self):
        Transaction.objects.create(
            user=self.user,
            title='Freelance',
            amount=750,
            transaction_type='income',
            date=date.today(),
            description='Project payment',
            category='Work',
        )
        Transaction.objects.create(
            user=self.user,
            title='Groceries',
            amount=250,
            transaction_type='expense',
            date=date.today(),
            description='Weekly groceries',
            category='Food',
        )

        response = self.client.get(reverse('profile'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['income'], 750)
        self.assertEqual(response.context['expense'], 250)
        self.assertEqual(response.context['balance'], 500)

    def test_profile_avatar_upload(self):
        avatar = SimpleUploadedFile(
            "avatar.png",
            b"\x89PNG\r\n\x1a\nfakepngdata",
            content_type="image/png",
        )

        response = self.client.post(reverse('profile'), {'avatar': avatar}, follow=True)

        self.assertEqual(response.status_code, 200)
        profile = UserProfile.objects.get(user=self.user)
        self.assertTrue(profile.avatar.name.startswith("avatars/"))

    def test_budget_alert_context_when_expense_crosses_threshold(self):
        profile = UserProfile.objects.create(user=self.user, monthly_budget=1000)
        Transaction.objects.create(
            user=self.user,
            title='Rent',
            amount=850,
            transaction_type='expense',
            date=date.today(),
            description='House rent',
            category='Housing',
        )

        response = self.client.get(reverse('profile'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['budget_alert']['status'], 'warning')
        self.assertEqual(profile.monthly_budget, 1000)

    def test_register_form_requires_special_character(self):
        form = RegisterForm(
            data={
                "username": "newuser",
                "email": "new@example.com",
                "password1": "Password123",
                "password2": "Password123",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("Password must include at least one special character.", form.errors["password1"])

    def test_register_invalid_submission_shows_error_message(self):
        response = self.client.post(
            reverse('register'),
            data={
                "username": "newuser",
                "email": "new@example.com",
                "password1": "Password123",
                "password2": "Password123",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Registration failed. Fix the highlighted fields and try again.")
        self.assertContains(response, "Password must include at least one special character.")

    def test_login_invalid_submission_shows_error_message(self):
        self.client.logout()
        response = self.client.post(
            reverse('login'),
            data={"username": "alice", "password": "wrongpass"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Login failed. Check your username and password and try again.")

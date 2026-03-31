from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
class Transaction(models.Model):
    TRANSACTION_TYPE =[
    ('income','Income'),
    ('expense','Expense'),
]
    user= models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPE)
    date = models.DateField()
    description = models.CharField(max_length=255)
    category = models.CharField(max_length=255)

    def __str__(self):
        return self.title   

class Goal(models.Model):
    user= models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    target_amount = models.DecimalField(max_digits=10, decimal_places=2)
    current_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    started_on = models.DateField(default=timezone.localdate)
    saved_on = models.DateField(default=timezone.localdate)
    deadline = models.DateField()
    

    def __str__(self):
        return self.title


class GoalContribution(models.Model):
    goal = models.ForeignKey(Goal, on_delete=models.CASCADE, related_name="contributions")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    saved_on = models.DateField(default=timezone.localdate)
    note = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-saved_on", "-created_at"]

    def __str__(self):
        return f"{self.goal.title} - {self.amount} on {self.saved_on}"


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    avatar = models.FileField(upload_to="avatars/", blank=True, null=True)
    monthly_budget = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} profile"

import uuid

from django.db import models
from django.utils import timezone


class CurrencyChoices(models.TextChoices):
    RUB = "RUB", "Russian ruble"
    USD = "USD", "US dollar"
    EUR = "EUR", "Euro"


class StatusChoices(models.TextChoices):
    CREATED = "created", "Created"
    PROCESSING = "processing", "In processing"
    PAID = "paid", "Paid"
    CANCELLED = "cancelled", "Cancelled"


class Payout(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    payment_amount = models.DecimalField(max_digits=10, decimal_places=2, null=False)
    currency = models.CharField(
        max_length=3, choices=CurrencyChoices.choices, default=CurrencyChoices.RUB
    )
    details = models.JSONField(
        null=True,
        blank=True,
        help_text="Recipient details in JSON format. Fields 'recipient_name' and 'method' required",
    )
    status = models.CharField(
        max_length=20, choices=StatusChoices.choices, default=StatusChoices.CREATED
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    comment = models.TextField(blank=True, null=True)

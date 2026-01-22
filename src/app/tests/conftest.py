import pytest
from rest_framework.test import APIClient

from src.app.models import CurrencyChoices


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def payout_data():
    return {
        "payment_amount": 100.00,
        "currency": "USD",
        "details": {"recipient_name": "Test User", "method": "bank_transfer"},
        "comment": "API test",
    }


@pytest.fixture
def service_payout_data():
    return {
        "payment_amount": 200.00,
        "currency": CurrencyChoices.RUB,
        "details": {"recipient_name": "Test User", "method": "card"},
        "comment": "Service test",
    }

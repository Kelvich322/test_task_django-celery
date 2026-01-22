import json
from unittest.mock import patch

import pytest
from django.urls import reverse
from rest_framework import status

from src.app.exceptions import InvalidStatusTransitionError
from src.app.models import CurrencyChoices, Payout, StatusChoices
from src.app.services import PayoutService


@pytest.mark.django_db
class TestPayoutModel:
    def test_payout_creation(self):
        payout = Payout.objects.create(
            payment_amount=100.00,
            currency=CurrencyChoices.USD,
            details={"recipient_name": "John Doe", "method": "bank_transfer"},
            status=StatusChoices.CREATED,
            comment="Test payment",
        )

        assert payout.payment_amount == 100.00
        assert payout.currency == CurrencyChoices.USD
        assert payout.status == StatusChoices.CREATED
        assert payout.id is not None
        assert payout.created_at is not None
        assert payout.updated_at is not None


@pytest.mark.django_db
class TestPayoutService:
    def test_create_payout_success(self, service_payout_data):
        """Test successful payout creation"""
        payout = PayoutService.create_payout(service_payout_data)
        assert payout.status == StatusChoices.CREATED
        assert payout.payment_amount == 200.00
        assert payout.currency == CurrencyChoices.RUB

    def test_submit_payout_success(self):
        payout = Payout.objects.create(
            payment_amount=150.00,
            currency=CurrencyChoices.USD,
            details={"recipient_name": "Jane Smith", "method": "paypal"},
            status=StatusChoices.CREATED,
        )

        with patch(
            "src.app.tasks.payout_task.process_single_payout_task.delay"
        ) as mock_task:
            PayoutService.submit_payout(payout.id)
            mock_task.assert_called_once_with(payout.id)

        payout.refresh_from_db()
        assert payout.status == StatusChoices.PROCESSING

    def test_submit_payout_invalid_status(self):
        payout = Payout.objects.create(
            payment_amount=100.00,
            currency=CurrencyChoices.EUR,
            details={"recipient_name": "Bob Johnson", "method": "bank"},
            status=StatusChoices.PROCESSING,
        )

        with pytest.raises(InvalidStatusTransitionError):
            PayoutService.submit_payout(payout.id)

    def test_submit_payout_missing_details(self):
        payout = Payout.objects.create(
            payment_amount=75.00,
            currency=CurrencyChoices.RUB,
            status=StatusChoices.CREATED,
        )

        with pytest.raises(ValueError):
            PayoutService.submit_payout(payout.id)


@pytest.mark.django_db
class TestPayoutViewSet:
    def test_create_payout_success(self, api_client, payout_data):
        with patch("src.app.tasks.payout_task.process_single_payout_task.delay"):
            response = api_client.post(
                reverse("payout-list"),
                data=json.dumps(payout_data),
                content_type="application/json",
            )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["status"] == StatusChoices.PROCESSING
        assert response.data["payment_amount"] == "100.00"

    def test_create_payout_invalid_amount(self, api_client, payout_data):
        invalid_data = payout_data.copy()
        invalid_data["payment_amount"] = -50.00

        response = api_client.post(
            reverse("payout-list"),
            data=json.dumps(invalid_data),
            content_type="application/json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "payment_amount" in response.data

    def test_delete_payout_invalid_status(self, api_client):
        payout = Payout.objects.create(
            payment_amount=100.00,
            currency=CurrencyChoices.USD,
            details={"recipient_name": "Test", "method": "card"},
            status=StatusChoices.PROCESSING,
        )

        response = api_client.delete(reverse("payout-detail", args=[str(payout.id)]))

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "error" in response.data

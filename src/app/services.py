import logging

from django.db import transaction

from src.app.exceptions import InvalidStatusTransitionError
from src.app.models import Payout, StatusChoices
from src.app.tasks import process_single_payout_task

logger = logging.getLogger(__name__)


class PayoutService:
    @staticmethod
    def create_payout(data):
        payout = Payout.objects.create(**data, status=StatusChoices.CREATED)
        logger.info(f"Payout created {payout.id}. Status: {payout.status}")
        return payout

    @staticmethod
    def submit_payout(payout_id):
        with transaction.atomic():
            payout = Payout.objects.select_for_update().get(id=payout_id)
            if payout.status != StatusChoices.CREATED:
                raise InvalidStatusTransitionError(
                    f"Unable to submit request from status {payout.status}"
                )

            if not payout.details or "recipient_name" not in payout.details:
                raise ValueError("Fill in the recipient's details")

            payout.status = StatusChoices.PROCESSING
            payout.save()
            logger.info(f"{Payout} {payout_id} send on processing")

        task = process_single_payout_task.delay(payout_id)
        logger.info(f"Run Celery-task {task.id} for payout {payout_id}")

        return payout

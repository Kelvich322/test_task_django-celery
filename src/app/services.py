import logging
import random
from django.db import transaction
from src.app.exceptions import InvalidStatusTransitionError
from src.app.models import Payout, StatusChoices

logger = logging.getLogger(__name__)


class PayoutService:
    @staticmethod
    def create_payout(data):
        payout = Payout.objects.create(**data, status=StatusChoices.CREATED)
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
        return payout


class PayoutProcessingService:
    @staticmethod
    def process_payouts_batch(batch_size=100):
        processing_payouts = Payout.objects.filter(
            status=StatusChoices.PROCESSING
        ).select_related("created_by")[:batch_size]
        stats = {
            "total_processed": 0,
            "approved": 0,
            "cancelled": 0,
        }

        if not processing_payouts:
            logger.info("There are no applications in the status PROCESSING")
            return None

        for payout in processing_payouts:
            try:
                result = PayoutProcessingService._process_single_payout(payout)

                if result["status"] == "approved":
                    stats["approved"] += 1
                elif result["status"] == "cancelled":
                    stats["cancelled"] += 1

                stats["total_processed"] += 1

            except Exception as e:
                logger.error(
                    f"Payment processing error {payout.id}: {e}",
                    exc_info=True,
                    extra={"payout_id": str(payout.id)},
                )

        logger.info(
            f"Payment processing completed. "
            f"Processed: {stats['total_processed']}, "
            f"Approved: {stats['approved']}, "
            f"Cancelled: {stats['cancelled']}"
        )

        return stats

    @staticmethod
    def _process_single_payout(payout: Payout):
        with transaction.atomic():
            locked_payout = Payout.objects.select_for_update().get(
                id=payout.id, status=StatusChoices.PROCESSING
            )
            is_approved = PayoutProcessingService._simulate_payment_gateway_check()

            if is_approved:
                locked_payout.status = StatusChoices.PAID
                result_status = "approved"
            else:
                locked_payout.status = StatusChoices.CANCELLED
                locked_payout.comment = "Rejected by the payment system"
                result_status = "cancelled"

            locked_payout.save()

        return {"status": result_status}

    @staticmethod
    def _simulate_payment_gateway_check():
        return random.random() < 0.8

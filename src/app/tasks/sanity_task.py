import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from src.app.models import Payout, StatusChoices
from src.app.tasks.payout_task import process_single_payout_task

logger = logging.getLogger(__name__)


@shared_task
def check_stalled_payouts():
    ten_minutes = timezone.now() - timedelta(minutes=10)

    stalled_payouts = Payout.objects.filter(
        status=StatusChoices.PROCESSING, updated_at__lt=ten_minutes
    )

    logger.info(f"Found {stalled_payouts.count()} stalled payouts in PROCESSING status")

    if stalled_payouts.count() == 0:
        return "No stalled payouts found"

    processed = 0
    for payout in stalled_payouts:
        try:
            task = process_single_payout_task.delay(payout.id)
            logger.info(
                f"Resubmitted stalled payout {payout.id}. Run Celery-task {task.id} "
            )
            processed += 1
        except Exception as e:
            logger.error(f"Failed to resubmit payout {payout.id}: {e}")
            payout.comment = f"Auto-check failed: {str(e)}"
            payout.status = StatusChoices.CANCELLED
            payout.save(update_fields=["comment", "status"])

    return f"Processed {processed} payouts"

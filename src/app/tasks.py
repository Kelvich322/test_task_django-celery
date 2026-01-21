import logging
import random
import time

from celery import shared_task
from celery.exceptions import MaxRetriesExceededError
from django.db import transaction

from .models import Payout, StatusChoices

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    name="payouts.process_single_payout",
    max_retries=3,
    default_retry_delay=60,
    soft_time_limit=300,
    time_limit=330,
)
def process_single_payout_task(self, payout_id):
    task_id = self.request.id
    try:
        logger.info(f"[Task {task_id}] Start processing payout:{payout_id}")
        delay_seconds = random.uniform(3, 10)
        logger.info(
            f"[Task {task_id}] Simulation of processing ({delay_seconds:.1f} seconds)"
        )
        time.sleep(delay_seconds)

        with transaction.atomic():
            payout = Payout.objects.select_for_update().get(
                id=payout_id, status=StatusChoices.PROCESSING
            )

            is_approved = random.random() < 0.8

            if is_approved:
                payout.status = StatusChoices.PAID
                payout.comment = f"Processed by Celery Task ID:{task_id}"
                result = "approved"
                logger.info(f"[Task {task_id}] Payoyt {payout_id} succesful")
            else:
                payout.status = StatusChoices.CANCELLED
                payout.comment = f"Cancelled by payout system. Task ID:{task_id}"
                result = "cancelled"
                logger.warning(f"[Task {task_id}] Payoyt {payout_id} was cancelled")

            payout.save()

            logger.info(
                f"[Task {task_id}] Payout {payout_id} was processed: new status -> {payout.status}"
            )

            return {
                "task_id": task_id,
                "payout_id": str(payout_id),
                "status": result,
                "new_status": payout.status,
                "processing_time": delay_seconds,
            }

    except Payout.DoesNotExist:
        error_msg = f"Payout {payout_id} not found or not in PROCESSING status"
        logger.error(f"[Task {task_id}] {error_msg}")
        raise
    except Exception as exc:
        logger.error(f"[Task {task_id}] Payment processing error {payout_id}: {exc}")

        try:
            self.retry(exc=exc, countdown=60)
        except MaxRetriesExceededError:
            logger.critical(f"[Task {task_id}] The task failed after all attempts.")

            with transaction.atomic():
                try:
                    payout = Payout.objects.get(id=payout_id)
                    payout.status = StatusChoices.CANCELLED
                    payout.comment = "Celery processing error after all attempts"
                    payout.save()
                except Exception as e:
                    logger.error(f"Change payout status error: {e}")

            raise

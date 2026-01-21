from rest_framework import serializers
from .models import Payout, StatusChoices


class PayoutSerializer(serializers.ModelSerializer):
    details = serializers.DictField(
    required=False,
    allow_null=True,
    help_text="Recipient details in JSON format. Fields 'recipient_name' and 'method' required",
    )
    class Meta:
        model = Payout
        fields = [
            "id",
            "payment_amount",
            "currency",
            "details",
            "status",
            "created_at",
            "updated_at",
            "comment",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_payment_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "The payment amount must be greater than zero."
            )
        return value

    def validate_details(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("The details must be in JSON format.")
        required_fields = ["recipient_name", "method"]
        for field in required_fields:
            if field not in value:
                raise serializers.ValidationError(
                    f"Field '{field}' required in details"
                )
        return value


class PayoutCreateSerializer(PayoutSerializer):
    class Meta(PayoutSerializer.Meta):
        read_only_fields = PayoutSerializer.Meta.read_only_fields + ["status"]


class PayoutUpdateSerializer(PayoutSerializer):
    class Meta(PayoutSerializer.Meta):
        read_only_fields = PayoutSerializer.Meta.read_only_fields + [
            "payment_amount",
            "currency",
        ]

    def validate_status(self, value):
        instance_status = self.instance.status if self.instance else None

        allowed_transitions = {
            StatusChoices.CREATED: [StatusChoices.PROCESSING, StatusChoices.CANCELLED],
            StatusChoices.PROCESSING: [StatusChoices.PAID, StatusChoices.CANCELLED],
            StatusChoices.PAID: [],
            StatusChoices.CANCELLED: [],
        }

        if instance_status and instance_status in allowed_transitions:
            if value not in allowed_transitions[instance_status]:
                raise serializers.ValidationError(
                    f"Invalid status transition from '{instance_status}' on '{value}'"
                )

        return value

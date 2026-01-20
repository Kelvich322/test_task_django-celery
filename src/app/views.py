from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from src.app.models import Payout, StatusChoices
from src.app.serializers import (
    PayoutSerializer,
    PayoutCreateSerializer,
    PayoutUpdateSerializer,
)
from src.app.services import PayoutService
from src.app.exceptions import InvalidStatusTransitionError


class PayoutViewSet(viewsets.ModelViewSet):
    queryset = Payout.objects.all()
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["status", "currency"]
    search_fields = ["comment", "details"]
    ordering_fields = ["created_at", "updated_at", "payment_amount"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.action == "create":
            return PayoutCreateSerializer
        elif self.action in ["update", "partial_update"]:
            return PayoutUpdateSerializer
        return PayoutSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        payout = PayoutService.create_payout(serializer.validated_data)

        response_serializer = PayoutSerializer(payout)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        try:
            if "status" in serializer.validated_data:
                new_status = serializer.validated_data["status"]

                if new_status == StatusChoices.PROCESSING:
                    PayoutService.submit_payout(instance.id)
                else:
                    instance.status = new_status
                    instance.save()
            else:
                for attr, value in serializer.validated_data.items():
                    setattr(instance, attr, value)
                instance.save()

            return Response(self.get_serializer(instance).data)

        except (InvalidStatusTransitionError, ValueError) as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()

        if instance.status not in [StatusChoices.CREATED, StatusChoices.CANCELLED]:
            return Response(
                {
                    "error": f"You cannot delete an application in the status {instance.status}"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        try:
            payout = PayoutService.submit_payout(pk)
            return Response(self.get_serializer(payout).data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

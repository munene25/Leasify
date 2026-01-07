from rest_framework import serializers
from utils.serializer import CamelCaseModelSerializer, CamelCaseSerializer
from .models import Payment


class PaymentSerializer(CamelCaseModelSerializer):
    class Meta:
        model = Payment
        exclude = ["full_name"]

class PaymentOverviewSerializer(CamelCaseSerializer):
    total_received = serializers.DecimalField(decimal_places=2, max_digits=10)
    total_expected = serializers.DecimalField(decimal_places=2, max_digits=10)
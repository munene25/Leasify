from rest_framework import serializers
from billing.choices import BillingStatus
from payments.models import Payment


class BillingListSerializer(serializers.Serializer):
    name = serializers.CharField()
    billing_id = serializers.IntegerField()
    tenancy_id = serializers.IntegerField()
    tenant_name = serializers.CharField(source="tenancy.user.full_name")
    status = serializers.ChoiceField(choices=BillingStatus.choices)
    duration_months = serializers.IntegerField()
    is_current = serializers.BooleanField()


class BillingDetailSerializer(serializers.Serializer):
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    total_due = serializers.DecimalField(max_digits=10, decimal_places=2)
    status = serializers.ChoiceField(choices=BillingStatus.choices)
    is_current = serializers.BooleanField()
    duration_months = serializers.IntegerField()

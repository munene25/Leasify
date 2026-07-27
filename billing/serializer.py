from rest_framework import serializers
from billing.choices import BillingStatus as BS


class BillingListSerializer(serializers.Serializer):
    name = serializers.CharField()
    billing_id = serializers.IntegerField(source="pk")
    tenancy_id = serializers.IntegerField()
    tenant_name = serializers.CharField(source="tenancy.user.full_name")
    status = serializers.ChoiceField(choices=BS.choices)
    duration_months = serializers.IntegerField()
    is_current = serializers.BooleanField()


class BillingDetailSerializer(serializers.Serializer):
    billing_id = serializers.IntegerField(source="pk")
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    total_due = serializers.DecimalField(max_digits=10, decimal_places=2)
    status = serializers.ChoiceField(choices=BS.choices)
    is_current = serializers.BooleanField()
    duration_months = serializers.IntegerField()

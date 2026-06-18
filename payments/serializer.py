from rest_framework import serializers
from payments.choices import PaymentStatus, PaymentMode
from billing.models import BillingPeriod as BP

class PaymentListSerializer(serializers.Serializer):
    """Serializer for listing payments"""
    id = serializers.IntegerField(source="pk")
    ref_no = serializers.CharField()
    billing_id = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    status = serializers.ChoiceField(choices=PaymentStatus.choices)
    phone_number = serializers.CharField()
    initiated_by = serializers.CharField()


class PaymentDetailSerializer(serializers.Serializer):
    """Serializer for payment detail"""
    id = serializers.IntegerField(source="pk")
    ref_no = serializers.CharField()
    billing_id = serializers.IntegerField()
    tenant_name = serializers.CharField(source="billing.tenancy.user.full_name")
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    status = serializers.ChoiceField(choices=PaymentStatus.choices)
    phone_number = serializers.CharField()
    initiated_by = serializers.CharField()
    receipt_no = serializers.CharField(allow_null=True, source="receipt_no", default=None)

class PaymentInitiateMpesaSerializer(serializers.Serializer):
    """Payment initiation serializer for M-Pesa STK push"""
    billing_id = serializers.IntegerField(source="billing.pk")
    phone_number = serializers.CharField()


class PaymentAltCreateSerializer(serializers.Serializer):
    """Serializer for manual payment creation (alternate mode: CASH/BANK)"""
    billing_id = serializers.PrimaryKeyRelatedField(queryset=BP.objects.all())
    mode = serializers.ChoiceField(choices=PaymentMode.choices, required=False)
    status = serializers.CharField(choices=PaymentStatus.choices)
    recorded_by = serializers.CharField()

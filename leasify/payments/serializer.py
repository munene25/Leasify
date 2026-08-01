from rest_framework import serializers
from leasify.payments.choices import PaymentStatus, PaymentMode
from leasify.common.fields import PhoneNumberSerializerField


class PaymentListSerializer(serializers.Serializer):
    """Serializer for listing payments"""

    payment_id = serializers.IntegerField(source="pk")
    billing_id = serializers.IntegerField()
    billing_name = serializers.CharField(source="billing.name")
    mode = serializers.CharField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    status = serializers.CharField()


class PaymentDetailSerializer(serializers.Serializer):
    """Serializer for payment detail"""

    payment_id = serializers.IntegerField(source="pk")
    billing_id = serializers.IntegerField()
    billing_name = serializers.CharField(source="billing.name")
    tenant_name = serializers.CharField(source="billing.tenancy.user.full_name")
    mode = serializers.CharField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    status = serializers.CharField()
    phone_number = serializers.CharField()
    receipt_no = serializers.CharField()


class PaymentInitiateMpesaSerializer(serializers.Serializer):
    """Payment initiation serializer for M-Pesa STK push"""

    billing_id = serializers.IntegerField()
    phone_number = PhoneNumberSerializerField()


class PaymentAltCreateSerializer(serializers.Serializer):
    """Serializer for manual payment creation (alternate mode: CASH/BANK)"""

    billing_id = serializers.IntegerField()
    mode = serializers.ChoiceField(choices=PaymentMode.choices)
    status = serializers.ChoiceField(choices=PaymentStatus.choices)

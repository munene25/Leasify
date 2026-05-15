from rest_framework import serializers
from common.fields import PhoneNumberSerializerField
from users.models import User
from apartments.models import Apartment
from tenancy.models import Tenancy


class TenancyListSerializer(serializers.Serializer):
    tenant_id = serializers.IntegerField(source="pk")
    tenant_name = serializers.CharField()
    apartment = serializers.CharField()
    payment_status = serializers.CharField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()

class TenancyCreateSerializer(serializers.Serializer):
    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    apartment = serializers.PrimaryKeyRelatedField(queryset=Apartment.objects.all())
    start_date = serializers.DateField()
    duration_months = serializers.IntegerField(min_value=1, max_value=4)

class TenancyDetailSerializer(serializers.Serializer):
    tenant_id = serializers.IntegerField(source="pk")
    tenant_name = serializers.CharField()
    phone_number = PhoneNumberSerializerField()
    apartment = serializers.CharField()
    payment_status = serializers.CharField()
    balance = serializers.DecimalField(max_digits=10, decimal_places=2)
    admission_date = serializers.DateTimeField(source="created_at")
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    lease_rent = serializers.DecimalField(max_digits=10, decimal_places=2)

class TenancyUpdateSerializer(serializers.Serializer):
    extension_months = serializers.IntegerField(min_value=1, max_value=4)
    apartment = serializers.PrimaryKeyRelatedField(queryset=Apartment.objects.all())

class TenancyExtendReservationSerializer(serializers.Serializer):
    reservation_extension = serializers.DurationField()
    tenancy = serializers.PrimaryKeyRelatedField(queryset=Tenancy.objects.all())

class TenancyTerminateSerializer(serializers.Serializer):
    tenancy = serializers.PrimaryKeyRelatedField(queryset=Tenancy.objects.all())
    termination_date = serializers.DateField(queryset=Apartment.objects.all())
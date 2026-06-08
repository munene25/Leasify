from users.models import User
from rest_framework import serializers
from apartments.models import Apartment
from tenancy.choices import TerminationReason


class TenancyListSerializer(serializers.Serializer):
    tenant_id = serializers.IntegerField(source="pk")
    tenant_name = serializers.CharField(source="user.full_name")
    apartment_name = serializers.CharField(source="apartment.apartment_name")
    status = serializers.CharField()
    date_joined = serializers.DateField()

class TenancyCreateSerializer(serializers.Serializer):
    apartment = serializers.PrimaryKeyRelatedField(queryset=Apartment.objects.all())
    start_date = serializers.DateField()
    duration_months = serializers.IntegerField(min_value=1, max_value=4)

class TenancyDetailSerializer(serializers.Serializer):
    tenant_id = serializers.IntegerField(source="pk")
    tenant_name = serializers.CharField(source="user.full_name")
    apartment_name = serializers.CharField(source="apartment.apartment_name")
    user_id = serializers.IntegerField()
    status = serializers.CharField()
    date_joined = serializers.DateField()
    paid_up_to = serializers.DateField()


class TenancyLeaseExtensionSerializer(serializers.Serializer):
    duration_months = serializers.IntegerField()

class TenancyTerminateSerializer(serializers.Serializer):
    termination_reason = serializers.ChoiceField(choices=TerminationReason)
    
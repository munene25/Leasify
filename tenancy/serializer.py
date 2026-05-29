from rest_framework import serializers
from common.fields import PhoneNumberSerializerField
from users.models import User
from apartments.models import Apartment
from tenancy.models import Tenancy


class TenancyListSerializer(serializers.Serializer):
    tenant_id = serializers.IntegerField(source="pk")
    tenant_name = serializers.CharField()
    apartment = serializers.CharField()
    status = serializers.CharField()
    date_joined = serializers.DateField()

class TenancyCreateSerializer(serializers.Serializer):
    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    apartment = serializers.PrimaryKeyRelatedField(queryset=Apartment.objects.all())
    start_date = serializers.DateField()
    duration_months = serializers.IntegerField(min_value=1, max_value=4)

class TenancyDetailSerializer(serializers.Serializer):
    tenant_id = serializers.IntegerField(source="pk")
    tenant_name = serializers.CharField()
    apartment = serializers.CharField()
    status = serializers.CharField()
    date_joined = serializers.DateField()
    phone_number = PhoneNumberSerializerField(source="user.account.phone_number")
    paid_up_to = serializers.DateField()


class TenancyLeaseExtensionSerializer(serializers.Serializer):
    duration_months = serializers.IntegerField()

from rest_framework import serializers

from common.fields import PhoneNumberSerializerField
from users.models import User
from apartments.models import Apartment
from semesters.models import Semester

# --- Shifted to primary key related fields to centralize object existence validation in serializers ---
# --- This is necessary only for input serializers ---

class TenancyListSerializer(serializers.Serializer):
    tenant_id = serializers.IntegerField(source="pk")
    tenant_name = serializers.CharField()
    apartment = serializers.CharField()
    payment_status = serializers.CharField()
    semester = serializers.CharField(source="semester.name")

class TenancyCreateSerializer(serializers.Serializer):
    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    semester = serializers.PrimaryKeyRelatedField(queryset=Semester.objects.all())
    apartment = serializers.PrimaryKeyRelatedField(queryset=Apartment.objects.all())

class TenancyDetailSerializer(serializers.Serializer):
    tenant_id = serializers.IntegerField(source="pk")
    tenant_name = serializers.CharField()
    phone_number = PhoneNumberSerializerField()
    apartment = serializers.CharField()
    payment_status = serializers.CharField()
    balance = serializers.DecimalField(max_digits=10, decimal_places=2)
    admission_date = serializers.DateTimeField(source="created_at")
    semester = serializers.CharField(source="semester.name")

class TenancyUpdateSerializer(serializers.Serializer):
    """I think its better to leave semester editing out of the tenancy once created."""
    # semester = serializers.PrimaryKeyRelatedField(queryset=Semester.objects.all())
    apartment = serializers.PrimaryKeyRelatedField(queryset=Apartment.objects.all())
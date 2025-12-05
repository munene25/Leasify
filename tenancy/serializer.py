from rest_framework import serializers
from utils import serializer
from semesters.serializer import SemesterListSerializer
from phonenumber_field.serializerfields import PhoneNumberField
from users.selectors import user_list
from apartments.selectors import apartment_list
from semesters.selectors import semester_list

# --- Shifted to primary key related fields to centralize object existence validation in serializers ---
# --- This is necessary only for input serializers ---

class TenancyListSerializer(serializer.Serializer):
    tenant_id = serializers.IntegerField(source="pk")
    tenant_name = serializers.CharField()
    apartment_name = serializers.CharField()
    payment_status = serializers.CharField()

class TenancyCreateSerializer(serializer.Serializer):
    user_id = serializers.PrimaryKeyRelatedField(queryset=user_list())
    semester_id = serializers.PrimaryKeyRelatedField(queryset=semester_list())
    apartment_id = serializers.PrimaryKeyRelatedField(queryset=apartment_list())

class TenancyDetailSerializer(serializer.Serializer):
    tenant_id = serializers.IntegerField(source="pk")
    tenant_name = serializers.CharField()
    phone_number = PhoneNumberField()
    apartment_name = serializers.CharField()
    payment_status = serializers.CharField()
    balance = serializers.DecimalField(max_digits=10, decimal_places=2)
    created_at = serializers.DateTimeField()
    semester = SemesterListSerializer()

class TenancyUpdateSerializer(serializer.Serializer):
    # All fields are optional
    apartment_id = serializers.IntegerField(required=False)
    semester_id = serializers.IntegerField(required=False)
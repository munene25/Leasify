from rest_framework import serializers
from utils import serializer
from semesters.serializer import SemesterListSerializer
from phonenumber_field.serializerfields import PhoneNumberField

class TenancyListSerializer(serializer.CamelCaseSerializer):
    tenant_id = serializers.IntegerField(source="pk")
    tenant_name = serializers.CharField()
    apartment_name = serializers.CharField()
    payment_status = serializers.CharField()

class TenancyCreateSerializer(serializer.CamelCaseSerializer):
    user_id = serializers.IntegerField()
    semester_id = serializers.IntegerField()
    apartment_id = serializers.IntegerField()

class TenancyDetailSerializer(serializer.CamelCaseSerializer):
    tenant_id = serializers.IntegerField(source="pk")
    tenant_name = serializers.CharField()
    phone_number = PhoneNumberField()
    apartment_name = serializers.CharField()
    date_joined = serializers.DateField()
    payment_status = serializers.CharField()
    balance = serializers.DecimalField(max_digits=10, decimal_places=2)
    semester = SemesterListSerializer()

class TenancyUpdateSerializer(serializer.CamelCaseSerializer):
    apartment_id = serializers.IntegerField(source="apartment", required=False)
    semester_id = serializers.IntegerField(source="semester", required=False)
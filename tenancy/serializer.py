from rest_framework import serializers

from semesters.serializer import SemesterListSerializer
from common.fields import PhoneNumberSerializerField
from users.models import User
from apartments.models import Apartment
from semesters.models import Semester

# --- Shifted to primary key related fields to centralize object existence validation in serializers ---
# --- This is necessary only for input serializers ---

class TenancyListSerializer(serializers.Serializer):
    tenant_id = serializers.IntegerField(source="pk")
    tenant_name = serializers.CharField()
    apartment_name = serializers.CharField()
    payment_status = serializers.CharField()

class TenancyCreateSerializer(serializers.Serializer):
    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    semester = serializers.PrimaryKeyRelatedField(queryset=Semester.objects.all())
    apartment = serializers.PrimaryKeyRelatedField(queryset=Apartment.objects.all())

class TenancyDetailSerializer(serializers.Serializer):
    tenant_id = serializers.IntegerField(source="pk")
    tenant_name = serializers.CharField()
    phone_number = PhoneNumberSerializerField()
    apartment_name = serializers.CharField()
    payment_status = serializers.CharField()
    balance = serializers.DecimalField(max_digits=10, decimal_places=2)
    admission_date = serializers.DateTimeField(source="created_at")
    semester = SemesterListSerializer()

class TenancyUpdateSerializer(serializers.Serializer):
    apartment_id = serializers.IntegerField()
    semester_id = serializers.IntegerField()
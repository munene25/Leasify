from utils.serializer import CamelCaseSerializer
from rest_framework import serializers
from tenancy.serializer import TenancyListSerializer

class ApartmentListSerializer(CamelCaseSerializer):
    apartment_id = serializers.IntegerField(source="id")
    apartment_name = serializers.CharField()
    rent = serializers.DecimalField(max_digits=10, decimal_places=2)
    rentable = serializers.BooleanField()

class ApartmentCreateSerializer(CamelCaseSerializer):
    block = serializers.CharField(required=True)
    unit_number = serializers.IntegerField(required=True)
    rent = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    rentable = serializers.BooleanField(required=False)

class ApartmentUpdateSerializer(CamelCaseSerializer):
    block = serializers.CharField(required=False)
    unit_number = serializers.IntegerField(required=False)
    rent = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    rentable = serializers.BooleanField(required=False)

class ApartmentDetailSerializer(CamelCaseSerializer):
    apartment_id = serializers.IntegerField(source="pk")
    block = serializers.CharField()
    unit_number = serializers.IntegerField()
    rent = serializers.DecimalField(max_digits=10, decimal_places=2)
    rentable = serializers.BooleanField()
    tenants = TenancyListSerializer(source="tenancy_set", many=True)

    
class ApartmentOverviewSerializer(CamelCaseSerializer):
    total_apartments = serializers.IntegerField()
    rentable = serializers.IntegerField()
    vacant = serializers.IntegerField()
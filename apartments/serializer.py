from rest_framework import serializers
from tenancy.serializer import TenancyListSerializer

class ApartmentListSerializer(serializers.Serializer):
    apartment_id = serializers.IntegerField(source="pk")
    apartment_name = serializers.CharField()
    rent = serializers.DecimalField(max_digits=10, decimal_places=2)
    rentable = serializers.BooleanField()

class ApartmentCreateSerializer(serializers.Serializer):
    block = serializers.CharField(required=True)
    unit_number = serializers.IntegerField(required=True)
    rent = serializers.DecimalField(max_digits=10, decimal_places=2, required=True)
    rentable = serializers.BooleanField(required=False)

class ApartmentUpdateSerializer(serializers.Serializer):
    block = serializers.CharField()
    unit_number = serializers.IntegerField()
    rent = serializers.DecimalField(max_digits=10, decimal_places=2)
    rentable = serializers.BooleanField()

class ApartmentDetailSerializer(serializers.Serializer):
    apartment_id = serializers.IntegerField(source="pk")
    block = serializers.CharField()
    unit_number = serializers.IntegerField()
    rent = serializers.DecimalField(max_digits=10, decimal_places=2)
    rentable = serializers.BooleanField()
    created_at = serializers.DateTimeField()
    tenants = TenancyListSerializer(source="tenancy_set", many=True)

    
class ApartmentOverviewSerializer(serializers.Serializer):
    total_apartments = serializers.IntegerField()
    rentable = serializers.IntegerField()
    vacant = serializers.IntegerField()
from rest_framework import serializers
from apartments.models import Apartment

class BlockValidator:
    def validate_block(self, data: str):
        string = data.upper()
        if string not in Apartment.ApartmentChoices.values:
            raise serializers.ValidationError(f"Only available choices are {Apartment.ApartmentChoices.values})")
        return string
    
class ApartmentListSerializer(serializers.Serializer):
    apartment_id = serializers.IntegerField(source="pk")
    apartment_name = serializers.CharField()
    rent = serializers.DecimalField(max_digits=10, decimal_places=2)
    rentable = serializers.BooleanField()
    occupied = serializers.BooleanField(allow_null=True)

class ApartmentCreateSerializer(serializers.Serializer, BlockValidator):
    block = serializers.CharField()
    unit_number = serializers.IntegerField()
    rent = serializers.DecimalField(max_digits=10, decimal_places=2)
    rentable = serializers.BooleanField(required=False, default=True)

class ApartmentUpdateSerializer(serializers.Serializer, BlockValidator):
    block = serializers.ChoiceField(choices=Apartment.ApartmentChoices.values)
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
    current_tenant = serializers.CharField(source="current_tenant.user.full_name", default=None)

    
class ApartmentOverviewSerializer(serializers.Serializer):
    total_apartments = serializers.IntegerField()
    rentable = serializers.BooleanField()
    vacant = serializers.IntegerField()
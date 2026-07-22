from rest_framework import serializers
from apartments.choices import Block, Wing
from tenancy.serializer import TenancyListSerializer

class ApartmentListSerializer(serializers.Serializer):
    apartment_id = serializers.IntegerField(source="pk")
    name = serializers.CharField()
    rent = serializers.DecimalField(max_digits=10, decimal_places=2)
    rentable = serializers.BooleanField()
    is_occupied = serializers.BooleanField(allow_null=True)


class ApartmentCreateSerializer(serializers.Serializer):
    block = serializers.ChoiceField(choices=Block.values)
    unit_number = serializers.IntegerField()
    floor = serializers.IntegerField()
    wing = serializers.ChoiceField(required=False, choices=Wing.values)
    rent = serializers.DecimalField(max_digits=10, decimal_places=2)
    rentable = serializers.BooleanField(required=False, default=True)


class ApartmentUpdateSerializer(serializers.Serializer):
    block = serializers.ChoiceField(choices=Block.values)
    unit_number = serializers.IntegerField()
    floor = serializers.IntegerField()
    rent = serializers.DecimalField(max_digits=10, decimal_places=2)
    rentable = serializers.BooleanField(allow_null=True)
    wing = serializers.ChoiceField(choices=Wing.values)


class ApartmentDetailSerializer(serializers.Serializer):
    apartment_id = serializers.IntegerField(source="pk")
    block = serializers.ChoiceField(choices=Block.values)
    unit_number = serializers.IntegerField()
    floor = serializers.IntegerField()
    wing = serializers.ChoiceField(choices=Wing.values)
    rent = serializers.DecimalField(max_digits=10, decimal_places=2)
    rentable = serializers.BooleanField()
    created_at = serializers.DateTimeField()
    current_tenant = TenancyListSerializer()


class ApartmentOverviewSerializer(serializers.Serializer):
    total_apartments = serializers.IntegerField()
    occupied = serializers.IntegerField()
    rentable = serializers.IntegerField()
    occupied = serializers.IntegerField()
    average_rent = serializers.DecimalField(max_digits=10, decimal_places=2)
    least_popular = serializers.CharField()
    most_popular = serializers.CharField()
    max_rent = serializers.DecimalField(max_digits=10, decimal_places=2)
    min_rent = serializers.DecimalField(max_digits=10, decimal_places=2)
    gross_expected_income = serializers.DecimalField(max_digits=10, decimal_places=2)

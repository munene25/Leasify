from rest_framework import serializers
from apartments.models import Apartment


class ApartmentListSerializer(serializers.Serializer):
    apartment_id = serializers.IntegerField(source="pk")
    apartment_name = serializers.CharField()
    rent = serializers.DecimalField(max_digits=10, decimal_places=2)
    rentable = serializers.BooleanField()
    is_occupied = serializers.BooleanField(allow_null=True)


class ApartmentCreateSerializer(serializers.Serializer):
    block = serializers.ChoiceField(choices=Apartment.ApartmentChoices.values)
    unit_number = serializers.IntegerField()
    rent = serializers.DecimalField(max_digits=10, decimal_places=2)
    rentable = serializers.BooleanField(required=False, default=True)


class ApartmentUpdateSerializer(serializers.Serializer):
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
    occupied = serializers.IntegerField()
    rentable = serializers.IntegerField()
    occupied = serializers.IntegerField()
    average_rent = serializers.DecimalField(max_digits=10, decimal_places=2)
    least_popular = serializers.CharField()
    most_popular = serializers.CharField()
    max_rent = serializers.DecimalField(max_digits=10, decimal_places=2)
    min_rent = serializers.DecimalField(max_digits=10, decimal_places=2)
    gross_expected_income = serializers.DecimalField(max_digits=10, decimal_places=2)

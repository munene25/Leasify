from rest_framework import serializers
from leasify.apartments.choices import Block, Wing
from leasify.tenancy.serializer import TenancyListSerializer

class ApartmentListSerializer(serializers.Serializer):
    apartment_id = serializers.IntegerField(source="pk")
    name = serializers.CharField()
    rent = serializers.DecimalField(max_digits=10, decimal_places=2)
    rentable = serializers.BooleanField()
    is_occupied = serializers.BooleanField(allow_null=True)


class ApartmentCreateSerializer(serializers.Serializer):
    block = serializers.ChoiceField(choices=Block.choices)
    unit_number = serializers.IntegerField()
    floor = serializers.IntegerField()
    wing = serializers.ChoiceField(required=False, choices=Wing.choices)
    rent = serializers.DecimalField(max_digits=10, decimal_places=2)
    rentable = serializers.BooleanField(required=False, default=True)


class ApartmentUpdateSerializer(serializers.Serializer):
    block = serializers.ChoiceField(choices=Block.choices)
    unit_number = serializers.IntegerField()
    floor = serializers.IntegerField()
    rent = serializers.DecimalField(max_digits=10, decimal_places=2)
    rentable = serializers.BooleanField(allow_null=True)
    wing = serializers.ChoiceField(choices=Wing.choices)


class ApartmentDetailSerializer(serializers.Serializer):
    apartment_id = serializers.IntegerField(source="pk")
    block = serializers.ChoiceField(choices=Block.choices)
    unit_number = serializers.IntegerField()
    floor = serializers.IntegerField()
    wing = serializers.ChoiceField(choices=Wing.choices)
    rent = serializers.DecimalField(max_digits=10, decimal_places=2)
    rentable = serializers.BooleanField()
    is_occupied = serializers.BooleanField()
    created_at = serializers.DateTimeField()
    current_tenant = TenancyListSerializer()


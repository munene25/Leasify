from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from utils.serializer import CamelCaseSerializer


class SemesterListSerializer(CamelCaseSerializer):
    semester_id = serializers.IntegerField(source="pk")
    name = serializers.CharField()
    rent = serializers.DecimalField(decimal_places=2, max_digits=10)


class SemesterDetailSerializer(CamelCaseSerializer):
    semester_id = serializers.IntegerField(source="pk")
    name = serializers.CharField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    rent = serializers.DecimalField(decimal_places=2, max_digits=10)
    active = serializers.BooleanField()


class SemesterUpdateSerializer(CamelCaseSerializer):
    name = serializers.CharField(required=False)
    rent = serializers.DecimalField(required=False, decimal_places=2, max_digits=10)
    update_apts = serializers.BooleanField(required=False)


class SemesterCreateSerializer(CamelCaseSerializer):
    name = serializers.CharField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    rent = serializers.DecimalField(decimal_places=2, max_digits=10, required=False)

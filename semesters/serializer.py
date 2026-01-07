from rest_framework import serializers

# Important distinction:
# All 'name' fields here are for the purpose of modifying the alt_name field
# Or representing the 'semester name'

class SemesterListSerializer(serializers.Serializer):
    semester_id = serializers.IntegerField(source="pk")
    name = serializers.CharField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    

class SemesterDetailSerializer(serializers.Serializer):
    semester_id = serializers.IntegerField(source="pk")
    name = serializers.CharField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    active = serializers.BooleanField()
    off_season = serializers.BooleanField()
    created_at = serializers.DateTimeField()

class SemesterUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(source="alt_name")
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    off_season = serializers.BooleanField()

class SemesterCreateSerializer(serializers.Serializer):
    name = serializers.CharField(source="alt_name", required=False)
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    off_season = serializers.BooleanField()

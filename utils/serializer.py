from rest_framework.serializers import Serializer, ModelSerializer
import re

class CamelCaseSerializer(Serializer):
    def to_representation(self, instance):
        initial = super().to_representation(instance)
        return to_camel_case_converter(initial)
    
    def to_internal_value(self, data):
        initial = super().to_internal_value(data)
        return to_snake_case_converter(initial=initial)
    
class CamelCaseModelSerializer(ModelSerializer):
    def to_representation(self, instance):
        initial = super().to_representation(instance)
        return to_camel_case_converter(initial)
    
    # def to_internal_value(self, data):
    #     initial = super().to_internal_value(data)
    #     return to_snake_case_converter(initial=initial)

def to_camel_case_converter(initial : dict) -> dict:
    output = {}
    for key, value in initial.items():
        parts = key.split("_")
        camel_key = parts[0] + "".join(part.capitalize() for part in parts[1:])
        output[camel_key] = value

    return output

def to_snake_case_converter(initial: dict) -> dict:
    output = {}
    for key, value in initial.items():
        parts = re.split(r'(?=[A-Z])', key)
        if len(parts) > 0:
            key = "_".join(p.lower() for p in parts if p)
        output[key] = value

    return output
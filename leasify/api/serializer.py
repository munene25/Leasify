from rest_framework import serializers
from leasify.common.fields import PhoneNumberSerializerField

class ContactSerializer(serializers.Serializer):
    """Regular login requires email and password"""

    email = serializers.EmailField()
    full_name = serializers.CharField()
    message = serializers.CharField()
    phone_number = PhoneNumberSerializerField(required=False)
    reply_url = serializers.URLField()

class ContactReplySerializer(serializers.Serializer):
    email = serializers.EmailField()
    full_name = serializers.CharField()
    message = serializers.CharField()
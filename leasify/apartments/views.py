from structlog import get_logger
from rest_framework import status
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny

from leasify.apartments import selectors as sl, serializer as sc
from leasify.common.views import BaseAPIView
from leasify.common.permissions import check_perms
from leasify.common.pagination import get_paginated_response

from leasify.apartments import services as sr
from leasify.apartments.choices import Block, Wing

logger = get_logger("apartments.views")


class ApartmentListCreateView(BaseAPIView):
    """
    Routes for listing the apartments adding apartments.
    Apartments are filtered based on which user is viewing.
    All apartments viewable by priviledged users, and rentable apartments for the rest.
    """
    class FilterSerializer(serializers.Serializer):
        block = serializers.CharField()
        wing = serializers.CharField()
        floor = serializers.IntegerField()
        unit_number = serializers.IntegerField()
        rentable = serializers.BooleanField(allow_null=True)
        order_by = serializers.CharField()
        rent_min = serializers.IntegerField()
        rent_max = serializers.IntegerField()

    serializer_class = sc.ApartmentCreateSerializer
    filter_class = FilterSerializer

    def get_permissions(self):
        """Only authenticated users during apartment creation, otherwise open to all."""
        return [IsAuthenticated() if self.request.method == "POST" else AllowAny()]

    def get(self, request):
        filters = self.validate_filter(data=request.query_params)
        qs = sl.apartment_list_for(user=request.user, filters=filters)
        return get_paginated_response(
            serializer_class=sc.ApartmentListSerializer, queryset=qs, request=request, view=self
        )

    def post(self, request):
        check_perms(request.user, "apartments.add_apartment")
        incoming = self.validate_serializer(data=request.data)
        apartment = sr.apartment_create(**incoming)
        outgoing = sc.ApartmentDetailSerializer(instance=apartment)
        return Response(data=outgoing.data, status=status.HTTP_201_CREATED)


class ApartmentDetailUpdateDeleteView(BaseAPIView):
    """
    All the routes here are priviledged.
    No need to allow users to view apartment details if no extra usefull information is being provided to unauathenticated users.
    """

    serializer_class = sc.ApartmentUpdateSerializer
    permission_classes = [IsAuthenticated]

    def get(self, request, apartment_id):
        check_perms(request.user, "apartments.view_apartment")
        selected = sl.apartment_get_for(user=request.user, apartment_id=apartment_id)
        outgoing = sc.ApartmentDetailSerializer(instance=selected)
        return Response(status=status.HTTP_200_OK, data=outgoing.data)

    def patch(self, request, apartment_id):
        check_perms(request.user, "apartments.change_apartment")

        incoming = self.validate_serializer(data=request.data, partial=True)
        selected = sl.apartment_get_for(user=request.user, apartment_id=apartment_id)

        apartment = sr.apartment_update(apartment=selected, **incoming)
        outgoing = sc.ApartmentDetailSerializer(instance=apartment)
        return Response(data=outgoing.data, status=status.HTTP_200_OK)

    def delete(self, request, apartment_id):
        check_perms(request.user, "apartments.delete_apartment")
        selected = sl.apartment_get_for(user=request.user, apartment_id=apartment_id)
        sr.apartment_delete(selected)
        return Response(
            status=status.HTTP_204_NO_CONTENT, data={"message": f"Apartment {str(selected)} deleted successfully"}
        )

class ApartmentChoicesView(BaseAPIView):

    permission_classes = []
    
    def get(self, request) -> Response:
        return Response({
            "block": [{"key": k, "display": v} for k, v in Block.choices],
            "wing": [{"key": k, "display": v} for k, v in Wing.choices],
        })
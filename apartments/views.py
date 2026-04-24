from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import serializers
from rest_framework import status
from common.views import BaseAPIView
from common.permissions import check_perms
from common.pagination import get_paginated_response
from semesters.selectors import semester_current
from apartments import selectors, services, serializer as sc
from structlog import get_logger

logger = get_logger("apartments.views")


class ApartmentListCreateView(BaseAPIView):
    """
    Routes for listing the apartments adding apartments.
    Apartments are filtered based on which user is viewing.
    All apartments viewable by priviledged users, and rentable apartments for the rest.
    """
    class FilterSerializer(serializers.Serializer):
        search = serializers.CharField()
        rentable = serializers.BooleanField(allow_null=True)
        order_by = serializers.CharField()
        rent_min = serializers.IntegerField()
        rent_max = serializers.IntegerField()

    serializer_class = sc.ApartmentCreateSerializer
    filter_class = FilterSerializer

    def get_permissions(self):
        """Only authenticated users during apartment creation, otherwise open to all."""
        return [IsAuthenticated()] if self.request.method == "POST" else [AllowAny()]

    def get(self, request):
        filters = self.validate_filter(data=request.query_params)
        qs = selectors.apartment_list_for(user=request.user, filters=filters)
        return get_paginated_response(
            serializer_class=sc.ApartmentListSerializer, queryset=qs, request=request, view=self
        )

    def post(self, request):
        check_perms(request.user, "apartments.add_apartment")
        incoming = self.validate_serializer(data=request.data)
        apartment = services.apartment_create(**incoming)
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
        """
        At this point, there is no new information provided in detail other than what the admin should view ie: current_tenant.
        Therefore it's better to just have it as an admin route.
        If anything changes, better to add view_apartment to the tenant's permission then serialize the instance differently based on the user.
        If this is the case, user rank based on their permission is more viable.
        """
        check_perms(request.user, "apartments.view_apartment")
        selected = selectors.apartment_get_for(user=request.user, apartment_id=apartment_id)
        outgoing = sc.ApartmentDetailSerializer(instance=selected)
        return Response(status=status.HTTP_200_OK, data=outgoing.data)

    def patch(self, request, apartment_id):
        check_perms(request.user, "apartments.change_apartment")

        incoming = self.validate_serializer(data=request.data, partial=True)
        selected = selectors.apartment_get_for(user=request.user, apartment_id=apartment_id)

        apartment = services.apartment_update(apartment=selected, **incoming)
        outgoing = sc.ApartmentDetailSerializer(instance=apartment)
        return Response(data=outgoing.data, status=status.HTTP_200_OK)

    def delete(self, request, apartment_id):
        check_perms(request.user, "apartments.delete_apartment")
        selected = selectors.apartment_get_for(user=request.user, apartment_id=apartment_id)
        services.apartment_delete(selected)
        return Response(
            status=status.HTTP_204_NO_CONTENT, data={"message": f"Apartment {str(selected)} deleted successfully"}
        )


class ApartmentOverviewView(BaseAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        check_perms(request.user, "apartments.view_overview")
        semester = semester_current()
        overview = selectors.apartment_overview(semester)

        serializer = sc.ApartmentOverviewSerializer(instance=overview)
        return Response(
            status=status.HTTP_200_OK,
            data=serializer.data,
        )

from rest_framework.response import Response
from common.views import BaseAPIView
from rest_framework import status
from semesters.selectors import semester_current
from apartments import selectors, services, serializer as sc
from rest_framework import serializers
from common.pagination import get_paginated_response
from common.permissions import check_perms
from rest_framework.permissions import IsAuthenticated, AllowAny
from structlog import get_logger

logger = get_logger("apartments.views")


class ApartmentListCreateView(BaseAPIView):
    class FilterSerializer(serializers.Serializer):
        search = serializers.CharField()
        rentable = serializers.BooleanField(allow_null=True)
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
            serializer_class=sc.ApartmentListSerializer, 
            queryset=qs, 
            request=request, 
            view=self
        )

    def post(self, request):
        check_perms(request.user, "apartments.add_apartment")
        incoming = self.validate_serializer(data=request.data)
        apartment = services.apartment_create(**incoming)
        outgoing = sc.ApartmentDetailSerializer(instance=apartment)
        logger.info(f"Admin added a new apartment {str(apartment)}")
        return Response(data=outgoing.data, status=status.HTTP_201_CREATED)


class ApartmentDetailUpdateDeleteView(BaseAPIView):
    serializer_class = sc.ApartmentUpdateSerializer
    permission_classes =[IsAuthenticated]


    def get(self, request, apartment_id):
        selected = selectors.apartment_get_for(user=request.user, apartment_id=apartment_id)
        outgoing = sc.ApartmentDetailSerializer(instance=selected)
        return Response(status=status.HTTP_200_OK, data=outgoing.data)

    def patch(self, request, apartment_id):
        check_perms(request.user, "apartments.change_apartment")

        incoming = self.validate_serializer(data=request.data, partial=True)
        selected = selectors.apartment_get_for(user=request.user, apartment_id=apartment_id)

        apartment = services.apartment_update(apartment=selected, **incoming)
        outgoing  = sc.ApartmentDetailSerializer(instance=apartment)
        return Response(data=outgoing.data, status=status.HTTP_200_OK)

    def delete(self, request, apartment_id):
        check_perms(request.user, "apartments.delete_apartment")
        selected = selectors.apartment_get_for(user=request.user, apartment_id=apartment_id)
        services.apartment_delete(apartment=selected)
        logger.warning(f"Admin deleted apartment {str(selected)}")
        return Response(status=status.HTTP_204_NO_CONTENT, data={"message": "Apartment deleted successfully"})


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

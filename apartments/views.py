from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from semesters.selectors import semester_current
from ..mixins.validate_serializer import ValidateSerializerMixin
from .models import Apartment
from . import selectors
from .services import ApartmentService
from .serializer import (
    ApartmentCreateSerializer,
    ApartmentDetailSerializer,
    ApartmentListSerializer,
    ApartmentOverviewSerializer,
    ApartmentUpdateSerializer,
)


class ApartmentListCreateView(APIView, ValidateSerializerMixin):
    serializer_class = ApartmentCreateSerializer

    def get(self, request):
        apts = selectors.apartment_list()
        serializer = ApartmentListSerializer(apts, many=True)
        return Response(status=status.HTTP_200_OK, data=serializer.data)

    def post(self, request):
        data = self.validate_input(data=request.data)
        ApartmentService().create(**data)
        return Response(status=status.HTTP_201_CREATED)


class ApartmentDetailUpdateDeleteView(APIView, ValidateSerializerMixin):    
    serializer_class = ApartmentUpdateSerializer

    def get(self, request, apartment_id):
        apt = selectors.apartment_get_by_id(apartment_id)
        serializer = ApartmentDetailSerializer(instance=apt)
        return Response(status=status.HTTP_200_OK, data=serializer.data)

    def patch(self, request, apartment_id):
        data = self.validate_input(data=request.data, partial=True)
        ApartmentService(apartment_id).update(**data)
        return Response(status=status.HTTP_200_OK)

    def put(self, request, apartment_id):
        data = self.validate_input(data=request.data)
        ApartmentService(apartment_id).update(**data)
        return Response(status=status.HTTP_200_OK)
    
    def delete(self, request, apartment_id):
        ApartmentService(apartment_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)



class ApartmentOverviewView(APIView):
    def get(self, request):
        semester = semester_current()
        overview = selectors.apartment_overview(semester.pk)

        serializer = ApartmentOverviewSerializer(instance=overview)
        return Response(
            status=status.HTTP_200_OK,
            data=serializer.data,
        )

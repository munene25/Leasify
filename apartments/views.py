from rest_framework.response import Response
from common.views import BaseAPIView
from rest_framework import status
from semesters.selectors import semester_current
from common.validators import validate_serializer
from . import selectors
from .services import ApartmentService
from .serializer import (
    ApartmentCreateSerializer,
    ApartmentDetailSerializer,
    ApartmentListSerializer,
    ApartmentOverviewSerializer,
    ApartmentUpdateSerializer,
)


class ApartmentListCreateView(BaseAPIView):
    serializer_class = ApartmentCreateSerializer

    def get(self, request):
        apts = selectors.apartment_list()
        serializer = ApartmentListSerializer(apts, many=True)
        return Response(status=status.HTTP_200_OK, data=serializer.data)

    def post(self, request):
        data = self.validate_serializer(data=request.data)
        ApartmentService().create(**data)
        return Response(status=status.HTTP_201_CREATED)


class ApartmentDetailUpdateDeleteView(BaseAPIView):
    serializer_class = ApartmentUpdateSerializer

    def get(self, request, apartment_id):
        apt = selectors.apartment_get_by_id(apartment_id)
        serializer = ApartmentDetailSerializer(instance=apt)
        return Response(status=status.HTTP_200_OK, data=serializer.data)

    def patch(self, request, apartment_id):
        data = validate_serializer(
            s_cls=self.serializer_class, data=request.data, partial=True
        )
        ApartmentService(apartment_id).update(**data)
        return Response(status=status.HTTP_200_OK)

    def put(self, request, apartment_id):
        data = self.validate_serializer(data=request.data)
        ApartmentService(apartment_id).update(**data)
        return Response(status=status.HTTP_200_OK)

    def delete(self, request, apartment_id):
        ApartmentService(apartment_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ApartmentOverviewView(BaseAPIView):
    def get(self, request):
        semester = semester_current()
        overview = selectors.apartment_overview(semester.pk)

        serializer = ApartmentOverviewSerializer(instance=overview)
        return Response(
            status=status.HTTP_200_OK,
            data=serializer.data,
        )

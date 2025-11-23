from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import serializers
from rest_framework import status
from semesters import selectors as semester_selectors
from . import selectors
from . import services
from .serializer import (
    ApartmentCreateSerializer,
    ApartmentDetailSerializer,
    ApartmentListSerializer,
    ApartmentOverviewSerializer,
    ApartmentUpdateSerializer,
)


class ApartmentListCreateView(APIView):
    def _validate_input(self, data):
        serializer = self.serializer_class(data=data)
        serializer.is_valid(raise_exception=True)
        return serializer.validated_data

    serializer_class = ApartmentCreateSerializer

    def get(self, request):
        apts = selectors.apartment_list()
        serializer = ApartmentListSerializer(apts, many=True)
        return Response(status=status.HTTP_200_OK, data=serializer.data)

    def post(self, request):
        data = self._validate_input(request.data)
        creator = services.ApartmentCreateService(**data)
        creator.create()
        return Response(status=status.HTTP_201_CREATED)


class ApartmentDetailUpdateView(APIView):
    def _validate_input(self, *, data):
        serializer = self.serializer_class(data=data)
        serializer.is_valid(raise_exception=True)
        return serializer.validated_data

    serializer_class = ApartmentUpdateSerializer

    def get(self, request, apartment_id):
        apt = selectors.apartment_get_by_id(apartment_id=apartment_id)
        serializer = ApartmentDetailSerializer(instance=apt)
        return Response(status=status.HTTP_200_OK, data=serializer.data)

    def patch(self, request, apartment_id):
        data = self._validate_input(data=request.data)
        updater = services.ApartmentUpdateService(apartment_id=apartment_id, **data)
        updater.update()
        return Response(status=status.HTTP_200_OK)

    def put(self, request, apartment_id):
        data = self._validate_input(data=request.data)
        updater = services.ApartmentUpdateService(apartment_id=apartment_id, **data)
        updater.update()
        return Response(status=status.HTTP_200_OK)


class ApartmentOverviewView(APIView):
    def get(self, request, semester_name=None):
        semester = semester_selectors.semester_get_by_name(semester_name=semester_name)
        overview = selectors.apartment_overview(semester=semester)

        serializer = ApartmentOverviewSerializer(instance=overview)
        return Response(
            status=status.HTTP_200_OK,
            data=serializer.data,
        )

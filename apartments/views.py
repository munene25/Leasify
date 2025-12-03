from rest_framework.response import Response
from typing import Any, Dict
from rest_framework.views import APIView
from rest_framework import status
from semesters.selectors import semester_current
from semesters.models import Semester
from . import selectors
from .services import ApartmentService
from .serializer import (
    ApartmentCreateSerializer,
    ApartmentDetailSerializer,
    ApartmentListSerializer,
    ApartmentOverviewSerializer,
    ApartmentUpdateSerializer,
)


class ApartmentListCreateView(APIView):
    serializer_class = ApartmentCreateSerializer

    def _validate_input(self, data):
        serializer = self.serializer_class(data=data)
        serializer.is_valid(raise_exception=True)
        v = serializer.validated_data
        return v if isinstance(v, dict) else {}
    
    def get(self, request):
        apts = selectors.apartment_list()
        serializer = ApartmentListSerializer(apts, many=True)
        return Response(status=status.HTTP_200_OK, data=serializer.data)

    def post(self, request):
        data = self._validate_input(request.data)
        ApartmentService().create(**data)
        return Response(status=status.HTTP_201_CREATED)


class ApartmentDetailUpdateView(APIView):
    def _validate_input(self, data):
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
        apt = selectors.apartment_get_for_update(apartment_id)
        ApartmentService(apt).update(**data) # type: ignore
        return Response(status=status.HTTP_200_OK)

    def put(self, request, apartment_id):
        data = self._validate_input(data=request.data)
        apt = selectors.apartment_get_for_update(apartment_id)
        ApartmentService(apt).update(**data) # type: ignore
        return Response(status=status.HTTP_200_OK)


class ApartmentOverviewView(APIView):
    def get(self, request):
        semester = semester_current()
        overview = selectors.apartment_overview(semester.pk)

        serializer = ApartmentOverviewSerializer(instance=overview)
        return Response(
            status=status.HTTP_200_OK,
            data=serializer.data,
        )

from rest_framework.response import Response
from rest_framework import status
from . import selectors
from . import services
from .serializer import (
    SemesterCreateSerializer,
    SemesterListSerializer,
    SemesterDetailSerializer,
    SemesterUpdateSerializer
)
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError


class SemesterListCreateView(APIView):
    serializer_class = SemesterCreateSerializer

    def _validate_input(self, data):
        serializer = self.serializer_class(data=data)
        serializer.is_valid(raise_exception=True)
        return serializer.validated_data
    
    def get(self, request):
        sems = selectors.semester_list()
        serializer = SemesterListSerializer(instance=sems, many=True)
        return Response(status=status.HTTP_200_OK, data=serializer.data)
    
    def post(self, request):
        data = self._validate_input(data=request.data)
        creator = services.SemesterCreateService(**data)
        creator.create()
        return Response(status=status.HTTP_201_CREATED)
    

class SemesterDetailUpdateView(APIView):
    serializer_class = SemesterUpdateSerializer

    def _validate_input(self, data):
        serializer = self.serializer_class(data=data)
        serializer.is_valid(raise_exception=True)
        return serializer.validated_data
    
    def get(self, request, semester_id):
        semester = selectors.semester_get_by_id(semester_id=semester_id)
        serializer = SemesterDetailSerializer(instance=semester)
        return Response(
            status=status.HTTP_200_OK,
            data=serializer.data
        )
    def patch(self, request, semester_id):
        data = self._validate_input(data=request.data)
        updater = services.SemesterUpdateService(semester_id=semester_id, **data)
        updater.update()
        return Response(status=status.HTTP_200_OK)
    
    def put(self, request, semester_id):
        data = self._validate_input(data=request.data)
        updater = services.SemesterUpdateService(semester_id=semester_id, **data)
        updater.update()
        return Response(status=status.HTTP_200_OK)
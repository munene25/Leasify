from rest_framework.response import Response
from rest_framework import status
from . import selectors
from . import services
from .serializer import (
    SemesterCreateSerializer,
    SemesterListSerializer,
    SemesterDetailSerializer,
    SemesterUpdateSerializer,
)
from common.views import BaseAPIView
from common.validators import validate_serializer


class SemesterListCreateView(BaseAPIView):
    serializer_class = SemesterCreateSerializer

    def get(self, request):
        sems = selectors.semester_list()
        serializer = SemesterListSerializer(instance=sems, many=True)
        return Response(status=status.HTTP_200_OK, data=serializer.data)

    def post(self, request):
        data = self.validate_serializer(data=request.data)
        creator = services.SemesterService().create(**data)
        return Response(status=status.HTTP_201_CREATED)


class SemesterDetailUpdateDeleteView(BaseAPIView):
    serializer_class = SemesterUpdateSerializer

    def get(self, request, semester_id: int):
        semester = selectors.semester_get_by_id(semester_id=semester_id)
        serializer = SemesterDetailSerializer(instance=semester)
        return Response(status=status.HTTP_200_OK, data=serializer.data)

    def patch(self, request, semester_id: int):
        data = validate_serializer(
            s_cls=self.serializer_class, data=request.data, partial=True
        )
        service = services.SemesterService(semester_id)
        service.update(**data)
        return Response(status=status.HTTP_200_OK)

    def put(self, request, semester_id):
        data = self.validate_serializer(data=request.data)
        service = services.SemesterService(semester_id)
        service.update(**data)
        return Response(status=status.HTTP_200_OK)

    def delete(self, request, semester_id: int):
        service = services.SemesterService(semester_id)
        service.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

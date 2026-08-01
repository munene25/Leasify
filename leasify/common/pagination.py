from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.serializers import Serializer
from django.db.models import QuerySet
from rest_framework.request import Request
from rest_framework.views import APIView

def get_paginated_response(*, serializer_class: type[Serializer], queryset: QuerySet, request: Request, view: APIView) -> Response:
    """Return paginated response for list views"""

    paginator = PageNumberPagination()
    page = paginator.paginate_queryset(queryset, request, view=view)

    if page is not None:
        serializer = serializer_class(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    serializer = serializer_class(queryset, many=True)

    return Response(data=serializer.data, status=200)

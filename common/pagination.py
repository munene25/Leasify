from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination

def get_paginated_response(*, serializer_class, queryset, request, view):
    paginator = PageNumberPagination()
    page = paginator.paginate_queryset(queryset, request, view=view)

    if page is not None:
        serializer = serializer_class(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    serializer = serializer_class(queryset, many=True)

    return Response(data=serializer.data)
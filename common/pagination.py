from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination

def get_paginated_response(*, s_cls, qs, req, view):
    paginator = PageNumberPagination()
    page = paginator.paginate_queryset(qs, req, view=view)

    if page is not None:
        serializer = s_cls(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    serializer = s_cls(qs, many=True)

    return Response(data=serializer.data)
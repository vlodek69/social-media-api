from rest_framework.pagination import PageNumberPagination


class BasicPagination(PageNumberPagination):
    page_size = 5
    max_page_size = 100

    def get_paginated_response(self, data):
        return {
            "links": {
                "next": self.get_next_link(),
                "previous": self.get_previous_link(),
            },
            "count": self.page.paginator.count,
            "results": data,
        }


def paginate_queryset(serializer, queryset, request):
    serializer_instance = serializer(
        queryset, many=True, context={"request": request}
    )
    paginator = BasicPagination()
    paginated_data = paginator.paginate_queryset(
        serializer_instance.data, request
    )
    return paginator.get_paginated_response(paginated_data)


class ListPagination(PageNumberPagination):
    page_size = 10
    max_page_size = 100

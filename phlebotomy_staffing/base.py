from requests.compat import urlencode
from rest_framework.views import APIView
from rest_framework.response import Response
from django.core.paginator import Paginator

class NewAPIView(APIView):
    """
    Base APIView with improved serializer handling and a safe partial update helper.
    """
    def get_serializer(self, *args, **kwargs):
        """
        Return the serializer instance that should be used for validating and
        deserializing input, and for serializing output.
        """
        serializer_class = self.get_serializer_class()
        kwargs.setdefault("context", self.get_serializer_context())
        return serializer_class(*args, **kwargs)

    def get_serializer_class(self):
        """
        Return the class to use for the serializer.
        Defaults to using `self.serializer_class`.
        """
        if getattr(self, 'swagger_fake_view', False):
            from rest_framework.serializers import Serializer
            return getattr(self, 'serializer_class', Serializer) or Serializer

        serializer_class = getattr(self, 'serializer_class', None)
        assert serializer_class is not None, (
            f"'{self.__class__.__name__}' should either include a `serializer_class` "
            "attribute, or override the `get_serializer_class()` method."
        )
        return serializer_class

    def get_serializer_context(self):
        """
        Extra context provided to the serializer class.
        """
        return {
            "request": self.request,
            "format": self.format_kwarg,
            "view": self,
        }

    def partial_update_object(self, instance, data: dict, fields: list = None):
        """
        Safely update only the allowed fields on a model instance from a dictionary.
        
        Why this exists:
          - Prevents accidental mass assignment of sensitive fields.
          - Handles cases where 'data' may contain extra keys.
          - More Pythonic and readable than manual setattr loop.
        """
        if fields is None:
            # If no fields list is provided, update everything in data (use with caution)
            fields = list(data.keys())

        updated = False
        for field in fields:
            if field in data:
                new_value = data[field]
                current_value = getattr(instance, field, None)

                if current_value != new_value:  # Only update if value actually changed
                    setattr(instance, field, new_value)
                    updated = True

        if updated:
            instance.save()  # Or instance.save(update_fields=fields) for better performance

        return instance


class AutoPaginatedResponse(Response):
    def __init__(self, data, request=None, **kwargs):
        if request and isinstance(data, list):

            query_params = request.query_params

            # =========================
            # 🔍 SEARCH (all fields)
            # =========================
            search_query = query_params.get("search")
            if search_query:
                search_query = search_query.lower()

                def match(item):
                    return any(
                        search_query in str(value).lower()
                        for value in item.values()
                    )

                data = list(filter(match, data))

            # =========================
            # 🎯 FILTERING (all fields)
            # =========================
            # Example: ?vehicle_type=suv&district=dhaka
            reserved_keys = {"page", "page_size", "search", "ordering"}

            for key, value in query_params.items():
                if key in reserved_keys:
                    continue

                data = [
                    item for item in data
                    if str(item.get(key, "")).lower() == value.lower()
                ]

            # =========================
            # ↕️ ORDERING
            # =========================
            ordering = query_params.get("ordering")
            if ordering:
                reverse = ordering.startswith("-")
                field = ordering.lstrip("-")

                try:
                    data.sort(
                        key=lambda x: x.get(field, None),
                        reverse=reverse
                    )
                except Exception:
                    pass  # ignore invalid fields

            # =========================
            # 📄 PAGINATION
            # =========================
            page = query_params.get("page", 1)
            page_size = query_params.get("page_size", 10)

            try:
                page_size = min(int(page_size), 100)
            except:
                page_size = 10

            paginator = Paginator(data, page_size)
            page_obj = paginator.get_page(page)


            def build_url(page_number):
                params = query_params.copy()
                params["page"] = page_number
                params["page_size"] = page_size
                return request.build_absolute_uri("?" + urlencode(params))


            next_url = build_url(page_obj.next_page_number()) if page_obj.has_next() else None
            prev_url = build_url(page_obj.previous_page_number()) if page_obj.has_previous() else None


            data = {
                "success": True,
                "pagination": {
                    "count": paginator.count,
                    "total_pages": paginator.num_pages,
                    "current_page": page_obj.number,
                    "next": next_url,
                    "previous": prev_url,
                },
                "results": list(page_obj)
            }

        super().__init__(data, **kwargs)

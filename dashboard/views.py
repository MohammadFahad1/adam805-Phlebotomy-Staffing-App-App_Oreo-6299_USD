from phlebotomy_staffing.base import NewAPIView
from rest_framework.response import Response
from rest_framework import status
from dashboard import serializers
from rest_framework.permissions import IsAuthenticated, IsAdminUser

# class DashboardView(NewAPIView):
#     serializer_class = serializers.DashboardHomeSerializer
#     permission_classes = [IsAdminUser]
#     http_method_names = ['get']
#     def get(self, request):
#         """
#         **
#         """
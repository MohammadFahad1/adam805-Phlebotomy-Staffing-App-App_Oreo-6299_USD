from phlebotomy_staffing.base import AutoPaginatedResponse, NewAPIView
from rest_framework.response import Response
from rest_framework import status
from appointments import serializers
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from authentication.serializers import EmptySerializer
from authentication.models import Client, ClientDocument, Phlebotomist, Phlebotomist_document
from django.contrib.auth import get_user_model
from django.db.models import Q
from rest_framework.views import APIView
from appointments.models import Appointment, PatientProfile, ServicePackage, ServicePackageFeature, Payment

User = get_user_model()

class ServicePackageListView(NewAPIView):
    serializer_class = serializers.ServicePackageListSerializer
    """
    List all service packages
    """
    def get(self, request):
        queryset = ServicePackage.objects.all()
        serializer = serializers.ServicePackageListSerializer(queryset, many=True)
        return AutoPaginatedResponse(serializer.data, request)


# Create appointment
class CreateAppointmentView(NewAPIView):
    serializer_class = serializers.AppointmentCreateSerializer
    permission_classes = [AllowAny]
    """
    Create a new appointment
    """
    def post(self, request):
        serializer = serializers.AppointmentCreateSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AppointmentListView(NewAPIView):
    serializer_class = serializers.AppointmentListSerializer
    permission_classes = [IsAuthenticated]
    """
    List all appointments. 
    
    - Filters by phlebotomists for logged in phlebotomists
    - Supports date filtering
    - Supports phlebotomist ID filtering
    """
    
    def get_queryset(self):
        queryset = Appointment.objects.all()
        
        user = self.request.user
        
        # Role-based filtering
        if user.role == User.CLIENT:
            queryset = queryset.none()
        elif user.role == User.PHLEBOTOMIST:
            # Get appointments for this phlebotomist
            queryset = queryset.filter(phlebotomist=user)
        
        # Date filtering
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date:
            queryset = queryset.filter(appointment_date__gte=start_date)
        
        if end_date:
            queryset = queryset.filter(appointment_date__lte=end_date)
        
        # Phlebotomist ID filtering
        phlebotomist_id = self.request.query_params.get('phlebotomist_id')
        if phlebotomist_id:
            queryset = queryset.filter(phlebotomist_id=phlebotomist_id)
        
        return queryset.select_related(
            'patient', 
            'service_package', 
            'phlebotomist'
        )
    
    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'start_date',
                openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                format='date',
                description='Filter by start date (YYYY-MM-DD)'
            ),
            openapi.Parameter(
                'end_date',
                openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                format='date',
                description='Filter by end date (YYYY-MM-DD)'
            ),
            openapi.Parameter(
                'phlebotomist_id',
                openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER,
                description='Filter by phlebotomist ID'
            )
        ]
    )
    def get(self, request):
        queryset = self.get_queryset()
        serializer = serializers.AppointmentListSerializer(queryset, many=True)
        return AutoPaginatedResponse(serializer.data, request)


class AppointmentDetailView(NewAPIView):
    serializer_class = serializers.AppointmentDetailSerializer
    permission_classes = [IsAuthenticated]
    """
    Retrieve a single appointment with full details including patient and phlebotomist information
    """
    
    def get_object(self):
        appointment_id = self.kwargs['pk']
        appointment = get_object_or_404(
            Appointment.objects.select_related('patient', 'service_package', 'phlebotomist'),
            id=appointment_id
        )
        
        # Authorization check
        user = self.request.user
        if user.role == User.CLIENT:
            self.permission_denied(self.request, "You don't have access to this appointment.")
        elif user.role == User.PHLEBOTOMIST:
            # Verify the phlebotomist is assigned to this appointment
            if appointment.phlebotomist != user:
                self.permission_denied(self.request, "You don't have access to this appointment.")
        
        return appointment
    
    def get(self, request, pk):
        appointment = self.get_object()
        serializer = serializers.AppointmentDetailSerializer(appointment)
        return Response(serializer.data)


class AppointmentStatusUpdateView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]
    """
    Update appointment status
    """
    
    def patch(self, request, pk):
        appointment = get_object_or_404(Appointment, id=pk)
        new_status = request.data.get('status')
        
        if new_status not in [choice[0] for choice in Appointment.STATUS_CHOICES]:
            return Response({'detail': 'Invalid status'}, status=status.HTTP_400_BAD_REQUEST)
        
        appointment.status = new_status
        appointment.save()
        
        return Response({'detail': f'Status updated to {new_status}'})

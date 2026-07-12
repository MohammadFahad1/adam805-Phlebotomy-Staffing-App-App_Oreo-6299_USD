from phlebotomy_staffing.base import NewAPIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from communication.models import Notification
from communication.notification_serializers import NotificationSerializer
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

class NotificationListAPIView(NewAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = NotificationSerializer

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter('is_read', openapi.IN_QUERY, description="Filter notifications by read status", type=openapi.TYPE_BOOLEAN, required=False)
        ],
        tags=['App (Common) - Notifications']
    )
    def get(self, request):
        """
        Get Notifications
        Retrieve a list of notifications for the authenticated user.
        """
        user = request.user
        notifications = Notification.objects.filter(user=user).order_by('-created_at')
        
        is_read_param = request.query_params.get('is_read')
        if is_read_param is not None:
            is_read = is_read_param.lower() == 'true'
            notifications = notifications.filter(is_read=is_read)
            
        serializer = self.serializer_class(notifications, many=True)
        return Response({
            "success": True,
            "data": serializer.data,
            "message": "Notifications retrieved successfully."
        }, status=status.HTTP_200_OK)

class NotificationUnreadCountAPIView(NewAPIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=['App (Common) - Notifications']
    )
    def get(self, request):
        """
        Get Unread Notifications Count
        Retrieve the count of unread notifications for the authenticated user.
        """
        user = request.user
        unread_count = Notification.objects.filter(user=user, is_read=False).count()
        return Response({
            "success": True,
            "data": {
                "unread_count": unread_count
            },
            "message": "Unread notification count retrieved successfully."
        }, status=status.HTTP_200_OK)

class NotificationMarkReadAPIView(NewAPIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter('notification_id', openapi.IN_QUERY, description="ID of the specific notification to mark as read. If not provided, all notifications will be marked as read.", type=openapi.TYPE_INTEGER, required=False)
        ],
        tags=['App (Common) - Notifications']
    )
    def post(self, request):
        """
        Mark Notifications as Read
        Mark a single notification or all notifications as read.
        """
        user = request.user
        notification_id = request.query_params.get('notification_id') or request.data.get('notification_id')
        
        if notification_id:
            try:
                notification = Notification.objects.get(id=notification_id, user=user)
                notification.is_read = True
                notification.save()
                return Response({
                    "success": True,
                    "message": "Notification marked as read successfully."
                }, status=status.HTTP_200_OK)
            except Notification.DoesNotExist:
                return Response({
                    "success": False,
                    "message": "Notification not found."
                }, status=status.HTTP_404_NOT_FOUND)
        else:
            # Mark all as read
            Notification.objects.filter(user=user, is_read=False).update(is_read=True)
            return Response({
                "success": True,
                "message": "All notifications marked as read successfully."
            }, status=status.HTTP_200_OK)

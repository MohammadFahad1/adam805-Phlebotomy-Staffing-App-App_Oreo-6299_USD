from django.urls import path, include
from rest_framework.routers import DefaultRouter
from fcm_django.api.rest_framework import FCMDeviceAuthorizedViewSet
from communication import views
from communication import notification_views

router = DefaultRouter()
router.register('devices', FCMDeviceAuthorizedViewSet, basename='devices')

urlpatterns = [
    path('', include(router.urls)),
    path('chats/', views.ChatListAPIView.as_view(), name='chat-list'),
    path('chats/<int:partner_id>/', views.MessageHistoryAPIView.as_view(), name='message-history'),
    path('chats/<int:partner_id>/seen/', views.MarkAsSeenAPIView.as_view(), name='mark-as-seen'),
    path('notifications/', notification_views.NotificationListAPIView.as_view(), name='notification-list'),
    path('notifications/unread-count/', notification_views.NotificationUnreadCountAPIView.as_view(), name='notification-unread-count'),
    path('notifications/mark-read/', notification_views.NotificationMarkReadAPIView.as_view(), name='notification-mark-read'),
]



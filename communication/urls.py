from django.urls import path
from communication import views

urlpatterns = [
    path('chats/', views.ChatListAPIView.as_view(), name='chat-list'),
    path('chats/<int:partner_id>/', views.MessageHistoryAPIView.as_view(), name='message-history'),
    path('chats/<int:partner_id>/seen/', views.MarkAsSeenAPIView.as_view(), name='mark-as-seen'),
]
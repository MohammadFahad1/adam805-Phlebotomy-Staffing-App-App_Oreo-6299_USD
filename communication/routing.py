from django.urls import path
from communication import consumers

websocket_urlpatterns = [
    path('ws/chat/user/<int:partner_id>/', consumers.ChatConsumer.as_asgi()),
]

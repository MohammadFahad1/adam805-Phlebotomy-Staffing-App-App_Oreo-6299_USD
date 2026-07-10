from rest_framework import serializers
from django.contrib.auth import get_user_model
from communication.models import Message

User = get_user_model()

class UserChatSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'full_name', 'email', 'role', 'profile_picture']

class MessageSerializer(serializers.ModelSerializer):
    sender = UserChatSerializer(read_only=True)
    receiver = UserChatSerializer(read_only=True)

    class Meta:
        model = Message
        fields = ['id', 'sender', 'receiver', 'job', 'message_text', 'is_read', 'is_seen', 'created_at']

class MessageCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ['message_text', 'job']

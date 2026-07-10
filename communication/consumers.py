import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import AccessToken
from communication.models import Message

User = get_user_model()

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.partner_id = self.scope['url_route']['kwargs']['partner_id']
        
        # 1. Inline JWT Authentication
        query_string = self.scope.get('query_string', b'').decode('utf-8')
        token = None
        for param in query_string.split('&'):
            if param.startswith('token='):
                token = param.split('=')[1]
                break

        if not token:
            await self.close()
            return

        try:
            access_token = AccessToken(token)
            user_id = access_token['user_id']
            # Fetch user inside database_sync_to_async
            self.user = await database_sync_to_async(User.objects.get)(id=user_id)
            self.scope['user'] = self.user
        except Exception:
            await self.close()
            return

        # 2. Construct deterministic room group name by sorting IDs
        user1 = min(self.user.id, self.partner_id)
        user2 = max(self.user.id, self.partner_id)
        self.room_group_name = f"chat_room_{user1}_{user2}"

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        data = json.loads(text_data)
        message_text = data.get('message_text', '')
        job_id = data.get('job_id', None)

        if not message_text.strip():
            return

        # Save message to DB
        msg = await self.save_message(self.user.id, self.partner_id, message_text, job_id)

        # Broadcast message to room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'id': msg.id,
                'sender_id': self.user.id,
                'receiver_id': self.partner_id,
                'message_text': message_text,
                'job_id': job_id,
                'created_at': msg.created_at.isoformat(),
                'is_read': msg.is_read
            }
        )

    async def chat_message(self, event):
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'id': event['id'],
            'sender_id': event['sender_id'],
            'receiver_id': event['receiver_id'],
            'message_text': event['message_text'],
            'job_id': event.get('job_id'),
            'created_at': event['created_at'],
            'is_read': event['is_read']
        }))

    @database_sync_to_async
    def save_message(self, sender_id, receiver_id, text, job_id):
        return Message.objects.create(
            sender_id=sender_id,
            receiver_id=receiver_id,
            message_text=text,
            job_id=job_id
        )

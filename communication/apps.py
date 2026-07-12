from django.apps import AppConfig


class CommunicationConfig(AppConfig):
    name = 'communication'

    def ready(self):
        from communication.signals import register_signals
        register_signals()

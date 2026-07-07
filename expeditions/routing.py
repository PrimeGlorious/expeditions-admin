from django.urls import path

from expeditions.consumers import ExpeditionEventsConsumer

websocket_urlpatterns = [
    path('ws/expeditions/', ExpeditionEventsConsumer.as_asgi()),
]

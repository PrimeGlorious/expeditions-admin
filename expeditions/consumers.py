from channels.generic.websocket import AsyncJsonWebsocketConsumer

from expeditions.events import user_group_name


class ExpeditionEventsConsumer(AsyncJsonWebsocketConsumer):
    """Stream expedition real-time events to a single authenticated user.

    Each connection joins the ``user_<id>`` group so that event dispatch can
    target recipients by user id, without subscribing anyone to expeditions
    they are not part of.
    """

    async def connect(self):
        user = self.scope.get('user')
        if user is None or not user.is_authenticated:
            await self.close()
            return
        self.group_name = user_group_name(user.id)
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        group_name = getattr(self, 'group_name', None)
        if group_name is not None:
            await self.channel_layer.group_discard(group_name, self.channel_name)

    async def expedition_event(self, event):
        await self.send_json(event['payload'])

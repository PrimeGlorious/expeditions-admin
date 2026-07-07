from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction

from expeditions import selectors

GROUP_PREFIX = 'user_'
CONSUMER_EVENT_TYPE = 'expedition.event'


def user_group_name(user_id):
    """Return the per-user channel group name for a given user id."""
    return f'{GROUP_PREFIX}{user_id}'


def _dispatch(*, expedition, payload):
    """Fan a client-facing payload out to every recipient's user group.

    The send is deferred with ``transaction.on_commit`` so events are only
    emitted after the surrounding database change has committed. Recipients are
    resolved from the committed state at emission time.
    """

    def _emit():
        channel_layer = get_channel_layer()
        if channel_layer is None:
            return
        recipient_ids = selectors.event_recipient_user_ids(expedition=expedition)
        for user_id in recipient_ids:
            async_to_sync(channel_layer.group_send)(
                user_group_name(user_id),
                {'type': CONSUMER_EVENT_TYPE, 'payload': payload},
            )

    transaction.on_commit(_emit)


def dispatch_member_invited(*, expedition, member_id):
    _dispatch(
        expedition=expedition,
        payload={
            'type': 'member_invited',
            'expedition_id': expedition.id,
            'member_id': member_id,
        },
    )


def dispatch_member_confirmed(*, expedition, member_id):
    _dispatch(
        expedition=expedition,
        payload={
            'type': 'member_confirmed',
            'expedition_id': expedition.id,
            'member_id': member_id,
        },
    )


def dispatch_expedition_status(*, expedition):
    _dispatch(
        expedition=expedition,
        payload={
            'type': 'expedition_status',
            'expedition_id': expedition.id,
            'status': expedition.status,
        },
    )

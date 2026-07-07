from rest_framework import serializers

from expeditions.models import Expedition, ExpeditionMember
from users.serializers import UserPublicSerializer


class ExpeditionMemberSerializer(serializers.ModelSerializer):
    user = UserPublicSerializer(read_only=True)

    class Meta:
        model = ExpeditionMember
        fields = ('id', 'user', 'state', 'invited_at', 'confirmed_at')
        read_only_fields = fields


class ExpeditionListSerializer(serializers.ModelSerializer):
    chief = UserPublicSerializer(read_only=True)

    class Meta:
        model = Expedition
        fields = (
            'id',
            'title',
            'status',
            'start_at',
            'end_at',
            'capacity',
            'chief',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class ExpeditionDetailSerializer(serializers.ModelSerializer):
    chief = UserPublicSerializer(read_only=True)
    members = ExpeditionMemberSerializer(many=True, read_only=True)

    class Meta:
        model = Expedition
        fields = (
            'id',
            'title',
            'description',
            'status',
            'start_at',
            'end_at',
            'capacity',
            'chief',
            'members',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class ExpeditionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Expedition
        fields = ('title', 'description', 'start_at', 'end_at', 'capacity')


class InviteMemberSerializer(serializers.Serializer):
    member_id = serializers.IntegerField()

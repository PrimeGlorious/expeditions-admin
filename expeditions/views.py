from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from expeditions import selectors, services
from expeditions.models import Expedition
from expeditions.serializers import (
    ExpeditionCreateSerializer,
    ExpeditionDetailSerializer,
    ExpeditionListSerializer,
    ExpeditionMemberSerializer,
    InviteMemberSerializer,
)
from users.models import User


@extend_schema_view(
    list=extend_schema(responses=ExpeditionListSerializer),
    retrieve=extend_schema(responses=ExpeditionDetailSerializer),
    create=extend_schema(
        request=ExpeditionCreateSerializer,
        responses={201: ExpeditionDetailSerializer},
    ),
)
class ExpeditionViewSet(viewsets.GenericViewSet):
    """REST interface over the expedition domain services.

    Views validate request shape, delegate every business rule to
    ``expeditions.services`` and serialize the result. Visibility is scoped so
    that a user only ever sees expeditions they lead or belong to; anything else
    resolves to a 404 rather than a leaked 403.
    """

    serializer_class = ExpeditionDetailSerializer
    queryset = Expedition.objects.all()

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Expedition.objects.none()
        return selectors.expeditions_visible_to(user=self.request.user)

    def get_serializer_class(self):
        if self.action == 'list':
            return ExpeditionListSerializer
        if self.action == 'create':
            return ExpeditionCreateSerializer
        if self.action == 'invite':
            return InviteMemberSerializer
        if self.action == 'confirm':
            return ExpeditionMemberSerializer
        return ExpeditionDetailSerializer

    def list(self, request):
        serializer = ExpeditionListSerializer(self.get_queryset(), many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        expedition = self.get_object()
        return Response(ExpeditionDetailSerializer(expedition).data)

    def create(self, request):
        serializer = ExpeditionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        expedition = services.create_expedition(
            chief=request.user, **serializer.validated_data
        )
        return Response(
            ExpeditionDetailSerializer(expedition).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        request=InviteMemberSerializer,
        responses={201: ExpeditionMemberSerializer},
    )
    @action(detail=True, methods=['post'])
    def invite(self, request, pk=None):
        expedition = self.get_object()
        serializer = InviteMemberSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        member = get_object_or_404(User, pk=serializer.validated_data['member_id'])
        membership = services.invite_member(
            expedition=expedition, chief=request.user, member=member
        )
        return Response(
            ExpeditionMemberSerializer(membership).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(request=None, responses=ExpeditionMemberSerializer)
    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        expedition = self.get_object()
        membership = services.confirm_invitation(
            expedition=expedition, member=request.user
        )
        return Response(ExpeditionMemberSerializer(membership).data)

    @extend_schema(request=None, responses=ExpeditionDetailSerializer)
    @action(detail=True, methods=['post'], url_path='set-ready')
    def set_ready(self, request, pk=None):
        expedition = self.get_object()
        expedition = services.set_ready(expedition=expedition, chief=request.user)
        return Response(ExpeditionDetailSerializer(expedition).data)

    @extend_schema(request=None, responses=ExpeditionDetailSerializer)
    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        expedition = self.get_object()
        expedition = services.start_expedition(
            expedition=expedition, chief=request.user
        )
        return Response(ExpeditionDetailSerializer(expedition).data)

    @extend_schema(request=None, responses=ExpeditionDetailSerializer)
    @action(detail=True, methods=['post'])
    def finish(self, request, pk=None):
        expedition = self.get_object()
        expedition = services.finish_expedition(
            expedition=expedition, chief=request.user
        )
        return Response(ExpeditionDetailSerializer(expedition).data)

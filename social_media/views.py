from django.contrib.auth import get_user_model
from django.db.models import Q
from django.shortcuts import render
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, \
    IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from social_media.models import Post
from social_media.serializers import (
    UserListSerializer,
    UserDetailSerializer,
    UserSubscriptionSerializer,
    PostSerializer,
)


class UserViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, GenericViewSet
):
    queryset = get_user_model().objects.all()

    def get_serializer_class(self):
        if self.action == "retrieve":
            return UserDetailSerializer

        if self.action in ["subscribe", "unsubscribe"]:
            return UserSubscriptionSerializer

        return UserListSerializer

    def get_queryset(self):
        """Filtering users by username or full name and by location"""
        user = self.request.query_params.get("user")
        location = self.request.query_params.get("location")

        queryset = self.queryset

        if user:
            queryset = queryset.filter(
                Q(username__icontains=user) | Q(full_name__icontains=user)
            )

        if location:
            queryset = queryset.filter(location__icontains=location)

        return queryset

    @action(
        methods=["GET"],
        detail=True,
        url_path="subscribe",
        permission_classes=[IsAuthenticated],
    )
    def subscribe(self, request, pk=None):
        """Endpoint for adding user to your subscriptions"""
        user_subscriptions = self.request.user.subscribed_to
        subscribe_to = self.get_object()

        if subscribe_to in user_subscriptions.all():
            return Response(
                "Already subscribed", status=status.HTTP_400_BAD_REQUEST
            )

        if subscribe_to == self.request.user:
            return Response(
                "Wil not subscribe to self", status=status.HTTP_400_BAD_REQUEST
            )

        user_subscriptions.add(subscribe_to)
        return Response("Subscribed!", status=status.HTTP_200_OK)

    @action(
        methods=["GET"],
        detail=True,
        url_path="unsubscribe",
        permission_classes=[IsAuthenticated],
    )
    def unsubscribe(self, request, pk=None):
        """Endpoint for removing user from your subscriptions"""
        user_subscriptions = self.request.user.subscribed_to
        unsubscribe_from = self.get_object()

        if unsubscribe_from not in user_subscriptions.all():
            return Response(
                "Not subscribed", status=status.HTTP_400_BAD_REQUEST
            )

        user_subscriptions.remove(unsubscribe_from)
        return Response("Unsubscribed!", status=status.HTTP_200_OK)


class PostViewSet(
    viewsets.ModelViewSet
):
    queryset = Post.objects.all()
    serializer_class = PostSerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

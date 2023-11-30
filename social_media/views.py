from django.contrib.auth import get_user_model
from django.shortcuts import render
from rest_framework import mixins
from rest_framework.viewsets import GenericViewSet

from social_media.serializers import UserListSerializer, UserDetailSerializer


class UserViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, GenericViewSet
):
    queryset = get_user_model().objects.all()
    # permission_classes = ()

    def get_serializer_class(self):
        if self.action == "retrieve":
            return UserDetailSerializer

        return UserListSerializer

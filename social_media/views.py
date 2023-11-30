from django.contrib.auth import get_user_model
from django.shortcuts import render
from rest_framework import mixins
from rest_framework.viewsets import GenericViewSet

from social_media.serializers import UserListSerializer


class UserViewSet(mixins.ListModelMixin, GenericViewSet):
    queryset = get_user_model().objects.all()

    def get_serializer_class(self):
        if self.action == "list":
            return UserListSerializer

        return UserListSerializer

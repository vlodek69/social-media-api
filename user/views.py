from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication

from user.serializers import (
    UserSerializer,
    ManageUserSerializer,
    UpdateUserPasswordSerializer,
    UpdateUserProfilePictureSerializer,
)


class CreateUserView(generics.CreateAPIView):
    serializer_class = UserSerializer


class ManageUserView(generics.RetrieveUpdateAPIView):
    serializer_class = ManageUserSerializer
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        return self.request.user


class UpdateUserPasswordView(generics.UpdateAPIView):
    serializer_class = UpdateUserPasswordSerializer
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        return self.request.user


class UpdateUserProfilePictureView(ManageUserView):
    serializer_class = UpdateUserProfilePictureSerializer

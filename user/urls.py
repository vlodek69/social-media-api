from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

from user.views import (
    CreateUserView,
    ManageUserView,
    UpdateUserPasswordView,
    UpdateUserProfilePictureView,
    BlacklistRefreshView,
)

app_name = "user"

urlpatterns = [
    path("register/", CreateUserView.as_view(), name="create"),
    path("login/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("token/verify/", TokenVerifyView.as_view(), name="token_verify"),
    path("logout/", BlacklistRefreshView.as_view(), name="logout"),
    path("me/", ManageUserView.as_view(), name="manage"),
    path(
        "me/update-password/",
        UpdateUserPasswordView.as_view(),
        name="update-password",
    ),
    path(
        "me/update-picture/",
        UpdateUserProfilePictureView.as_view(),
        name="update-picture",
    ),
]

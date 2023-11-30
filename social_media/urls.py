from django.urls import path
from rest_framework import routers

from social_media.views import UserViewSet

router = routers.DefaultRouter()

router.register("users", UserViewSet)

urlpatterns = router.urls

app_name = "social_media"

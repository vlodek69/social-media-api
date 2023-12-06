from django.urls import path
from rest_framework import routers

from social_media.views import UserViewSet, PostViewSet, CommentViewSet

router = routers.DefaultRouter()

router.register("users", UserViewSet)
router.register("posts", PostViewSet)
router.register("comments", CommentViewSet)

urlpatterns = router.urls

app_name = "social_media"

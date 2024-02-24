from rest_framework import routers

from social_media.views import UserViewSet, PostViewSet, CommentViewSet


view_set_dict = {
    "users": UserViewSet,
    "posts": PostViewSet,
    "comments": CommentViewSet,
}

router = routers.DefaultRouter()

for view_set_prefix, view_set_class in view_set_dict.items():
    router.register(view_set_prefix, view_set_class)

urlpatterns = router.urls

app_name = "social_media"

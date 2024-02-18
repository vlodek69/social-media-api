from django.contrib.auth import get_user_model
from django.db.models import Q
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiParameter,
    extend_schema,
)
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import (
    IsAuthenticated,
    IsAuthenticatedOrReadOnly,
)
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from social_media.models import Post, Comment
from social_media.paginators import ListPagination
from social_media.permissions import IsOwnerOrReadOnly
from social_media.serializers import (
    UserListSerializer,
    UserDetailSerializer,
    UserSubscriptionSerializer,
    PostSerializer,
    CommentSerializer,
    PostDetailSerializer,
    CommentDetailSerializer,
    PostListSerializer,
    PostScheduleSerializer,
    TaskSerializer,
    UserWithPostsSerializer,
    LikeSerializer,
)
from social_media.tasks import schedule_post_create


class UserViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, GenericViewSet
):
    queryset = get_user_model().objects.prefetch_related(
        "liked_comments", "liked_posts"
    )
    permission_classes = (IsAuthenticatedOrReadOnly,)
    pagination_class = ListPagination

    def get_serializer_class(self):
        if self.action == "retrieve":
            return UserDetailSerializer

        if self.action == "with_posts":
            return UserWithPostsSerializer

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

    def perform_subscribe_action(self, subscribe_to, request, action_type):
        serializer = self.get_serializer(
            data={"subscribe_to": subscribe_to.id},
            context={"request": request, "action": action_type},
        )
        serializer.is_valid(raise_exception=True)
        result = serializer.perform_action(subscribe_to, request)
        return Response(result["message"], status=status.HTTP_200_OK)

    @action(
        methods=["POST"],
        detail=True,
        url_path="subscribe",
        permission_classes=[IsAuthenticated],
    )
    def subscribe(self, request, pk=None):
        """Endpoint for adding user to your subscriptions"""
        subscribe_to = self.get_object()
        return self.perform_subscribe_action(
            subscribe_to, request, action_type="subscribe"
        )

    @action(
        methods=["POST"],
        detail=True,
        url_path="unsubscribe",
        permission_classes=[IsAuthenticated],
    )
    def unsubscribe(self, request, pk=None):
        """Endpoint for removing user from your subscriptions"""
        subscribe_to = self.get_object()
        return self.perform_subscribe_action(
            subscribe_to, request, action_type="unsubscribe"
        )

    @action(
        methods=["GET"],
        detail=True,
        url_path="with-posts",
        permission_classes=[IsAuthenticatedOrReadOnly],
    )
    def with_posts(self, request, pk=None):
        """Endpoint for showing user's posts"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @extend_schema(
        parameters=[
            OpenApiParameter(
                "user",
                type=OpenApiTypes.STR,
                description=(
                    "Filter by username or full name " "(ex. ?user=John+Doe)"
                ),
            ),
            OpenApiParameter(
                "location",
                type=OpenApiTypes.STR,
                description=(
                    "Filter by user's location " "(ex. ?location=Kyiv)"
                ),
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class LikeMixin:
    def perform_like_action(self, obj, request, action_type):
        is_post = isinstance(obj, Post)  # to distinguish Post and Comment
        serializer = self.get_serializer(
            data={},
            context={
                "request": request,
                "action": action_type,
                "obj": obj.id,
                "is_post": is_post,
            },
        )
        serializer.is_valid(raise_exception=True)
        result = serializer.perform_action(obj, request)
        return Response(result["message"], status=status.HTTP_200_OK)

    @action(
        methods=["POST"],
        detail=True,
        url_path="like",
        permission_classes=[IsAuthenticated],
    )
    def like(self, request, pk=None):
        """Endpoint for adding post to your liked_posts"""
        obj = self.get_object()
        return self.perform_like_action(obj, request, action_type="like")

    @action(
        methods=["POST"],
        detail=True,
        url_path="unlike",
        permission_classes=[IsAuthenticated],
    )
    def unlike(self, request, pk=None):
        """Endpoint for removing post from your liked_posts"""
        obj = self.get_object()
        return self.perform_like_action(obj, request, action_type="unlike")


class PostViewSet(LikeMixin, viewsets.ModelViewSet):
    queryset = Post.objects.prefetch_related(
        "comments__users_liked", "users_liked", "comments__user"
    ).select_related("user")
    permission_classes = (
        IsAuthenticatedOrReadOnly,
        IsOwnerOrReadOnly,
    )
    pagination_class = ListPagination

    def get_liked_posts(self, queryset):
        """Returns queryset with liked posts and posts that have liked
        comments"""
        liked_posts = queryset.filter(
            id__in=self.request.user.liked_posts.all()
        )
        liked_comment_posts = queryset.filter(
            comments__in=self.request.user.liked_comments.all()
        )
        return liked_comment_posts.union(liked_posts)

    def get_queryset(self):
        """Filter posts by subscriptions and likes"""
        queryset = self.queryset

        if self.action == "subscriptions":
            queryset = queryset.filter(
                user__in=self.request.user.subscribed_to.all()
            )

        if self.action == "liked":
            queryset = self.get_liked_posts(queryset)

        return queryset.order_by("-created_at")

    def perform_create(self, serializer):
        """Create Post instance with currently authenticated user as value in
        'user' field"""
        serializer.save(user=self.request.user)

    def get_serializer_class(self):
        if self.action == "schedule":
            return PostScheduleSerializer

        if self.action in ("list", "subscriptions", "liked"):
            return PostListSerializer

        if self.action == "retrieve":
            return PostDetailSerializer

        if self.action == "comment":
            return CommentSerializer

        if self.action in ("like", "unlike"):
            return LikeSerializer

        return PostSerializer

    @action(
        methods=["POST"],
        detail=False,
        url_path="schedule",
        permission_classes=[IsAuthenticated],
    )
    def schedule(self, request, pk=None):
        """Endpoint for creating a scheduled Post"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        task_data = TaskSerializer.serialize_task_data(request)

        schedule_post_create.apply_async(
            (
                task_data["user_id"],
                task_data["request_data"],
                task_data["media_path"],
            ),
            countdown=task_data["countdown"],
        )
        return Response("Post is scheduled!", status=status.HTTP_200_OK)

    @action(
        methods=["POST"],
        detail=True,
        url_path="comment",
        permission_classes=[IsAuthenticated],
    )
    def comment(self, request, pk=None):
        """Endpoint for creating new Comment with prefilled 'user' and 'post'
        fields"""
        comment = self.get_serializer(data=request.data)
        comment.is_valid(raise_exception=True)
        comment.save(user=self.request.user, post=self.get_object())
        return Response(comment.data, status=status.HTTP_200_OK)

    @action(
        methods=["GET"],
        detail=False,
        url_path="my-feed",
        permission_classes=[IsAuthenticated],
    )
    def subscriptions(self, request, pk=None):
        """Endpoint for displaying posts of only subscribed to users"""
        return super().list(request)

    @action(
        methods=["GET"],
        detail=False,
        url_path="liked",
        permission_classes=[IsAuthenticated],
    )
    def liked(self, request, pk=None):
        """Endpoint for displaying liked posts"""
        return super().list(request)


class CommentViewSet(
    LikeMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    GenericViewSet,
):
    queryset = Comment.objects.prefetch_related(
        "users_liked",
    ).select_related("user", "post__user")
    permission_classes = (
        IsAuthenticatedOrReadOnly,
        IsOwnerOrReadOnly,
    )
    pagination_class = ListPagination

    def get_serializer_class(self):
        if self.action == "retrieve":
            return CommentDetailSerializer

        if self.action in ("like", "unlike"):
            return LikeSerializer

        return CommentSerializer

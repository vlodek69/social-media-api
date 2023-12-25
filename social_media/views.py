from datetime import datetime, timedelta

from django.contrib.auth import get_user_model
from django.db.models import Q
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiParameter,
    extend_schema,
)
from pytz import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import (
    IsAuthenticated,
    IsAuthenticatedOrReadOnly,
)
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from social_media.models import Post, Comment
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
    CommentListSerializer,
    UserWithPostsSerializer,
)
from social_media.tasks import schedule_post_create


class BasicPagination(PageNumberPagination):
    page_size = 10
    max_page_size = 100


class UserViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, GenericViewSet
):
    queryset = get_user_model().objects.all()
    permission_classes = (IsAuthenticatedOrReadOnly,)
    pagination_class = BasicPagination

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
        # return super().retrieve(request, *args, **kwargs)
        # serializer = self.get_serializer(data=request.data)
        # return Response(serializer.data, status=status.HTTP_200_OK)

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


def can_edit(obj: Post | Comment, minutes_to_edit: int = 5) -> bool:
    """Returns True if Post/Comment was created less than 'minutes_to_edit'
    minutes ago"""
    return datetime.now(tz=timezone("UTC")) - obj.created_at < timedelta(
        minutes=minutes_to_edit
    )


class LikeMixin:
    def get_user_liked_posts(self):
        # This method should be overridden in the view set
        return self.request.user.liked_posts

    @action(
        methods=["GET"],
        detail=True,
        url_path="like",
        permission_classes=[IsAuthenticated],
    )
    def like(self, request, pk=None):
        """Endpoint for adding post to your liked_posts"""
        user_liked_posts = self.get_user_liked_posts()
        post = self.get_object()

        if post in user_liked_posts.all():
            return Response(
                "Already liked", status=status.HTTP_400_BAD_REQUEST
            )

        user_liked_posts.add(post)
        return Response("Liked!", status=status.HTTP_200_OK)

    @action(
        methods=["GET"],
        detail=True,
        url_path="unlike",
        permission_classes=[IsAuthenticated],
    )
    def unlike(self, request, pk=None):
        """Endpoint for removing post from your liked_posts"""
        user_liked_posts = self.get_user_liked_posts()
        post = self.get_object()

        if post not in user_liked_posts.all():
            return Response("Not liked", status=status.HTTP_400_BAD_REQUEST)

        user_liked_posts.remove(post)
        return Response("Unliked!", status=status.HTTP_200_OK)


class CommentPagination(PageNumberPagination):
    page_size = 5
    page_size_query_param = "comment_page_size"
    max_page_size = 100


class PostViewSet(LikeMixin, viewsets.ModelViewSet):
    queryset = Post.objects.all()
    permission_classes = (
        IsAuthenticatedOrReadOnly,
        IsOwnerOrReadOnly,
    )
    pagination_class = BasicPagination

    def get_liked_posts(self, queryset):
        """Returns queryset with liked posts and posts that have liked
        comments"""
        liked_posts = self.request.user.liked_posts.all()
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
        if serializer.is_valid():
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
        else:
            return Response(
                serializer.errors, status=status.HTTP_400_BAD_REQUEST
            )

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

        if comment.is_valid():
            comment.save(user=self.request.user, post=self.get_object())
            return Response(comment.data, status=status.HTTP_200_OK)

        return Response(comment.errors, status=status.HTTP_400_BAD_REQUEST)

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

    def update(self, request, *args, **kwargs):
        """Allow update only for 5 minutes after Post creation"""
        if can_edit(self.get_object()):
            return super().update(request, *args, **kwargs)

        return Response(
            {"Cannot edit after 5 minutes"}, status=status.HTTP_403_FORBIDDEN
        )

    @extend_schema(
        parameters=[OpenApiParameter("page", OpenApiTypes.INT)],
    )
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()

        comments = Comment.objects.filter(post=instance).order_by(
            "-created_at"
        )
        paginator = CommentPagination()
        result_page = paginator.paginate_queryset(comments, request)

        post_serializer = self.get_serializer(instance)
        comments_serializer = CommentListSerializer(
            result_page, many=True, context={"request": request}
        )
        data = post_serializer.data
        data["comments"] = comments_serializer.data

        return paginator.get_paginated_response(data)


class CommentViewSet(
    LikeMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    GenericViewSet,
):
    queryset = Comment.objects.all()
    permission_classes = (
        IsAuthenticatedOrReadOnly,
        IsOwnerOrReadOnly,
    )
    pagination_class = BasicPagination

    def get_user_liked_posts(self):
        return self.request.user.liked_comments

    def get_serializer_class(self):
        if self.action == "retrieve":
            return CommentDetailSerializer

        return CommentSerializer

    def update(self, request, *args, **kwargs):
        """Allow update only for 5 minutes after Comment creation"""
        if can_edit(self.get_object()):
            return super().update(request, *args, **kwargs)

        return Response(
            {"Cannot edit after 5 minutes"}, status=status.HTTP_403_FORBIDDEN
        )

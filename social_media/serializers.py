from typing import Dict, Any

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import InMemoryUploadedFile
from rest_framework import serializers
from datetime import datetime, timedelta
from django.utils import timezone as django_timezone

from social_media.models import Post, Comment
from social_media.paginators import paginate_queryset


class UserListSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = (
            "id",
            "username",
            "full_name",
            "profile_picture",
            "subscribers_count",
        )


class UserPostSerializer(UserListSerializer):
    class Meta:
        model = get_user_model()
        fields = ("id", "profile_picture", "full_name", "username")


class UserDetailSerializer(serializers.ModelSerializer):
    subscribed_to = UserListSerializer(many=True)
    subscribers = UserListSerializer(many=True)

    class Meta:
        model = get_user_model()
        fields = (
            "id",
            "profile_picture",
            "username",
            "full_name",
            "bio",
            "location",
            "website",
            "subscribers_count",
            "subscribers",
            "subscribed_to",
        )


class UserSubscriptionSerializer(serializers.Serializer):
    subscribe_to = serializers.PrimaryKeyRelatedField(
        queryset=get_user_model().objects.all()
    )

    def validate_subscribe_to(self, subscribe_to):
        request = self.context.get("request")
        action = self.context.get("action")

        user_subscriptions = request.user.subscribed_to.all()

        if action == "subscribe":
            if subscribe_to in user_subscriptions:
                raise serializers.ValidationError("Already subscribed")

            if subscribe_to == request.user:
                raise serializers.ValidationError("Wil not subscribe to self")
        elif (
            action == "unsubscribe" and subscribe_to not in user_subscriptions
        ):
            raise serializers.ValidationError("Not subscribed")

        return subscribe_to

    def perform_action(self, subscribe_to, request):
        action = self.context.get("action")

        if action == "subscribe":
            request.user.subscribed_to.add(subscribe_to)
            return {
                "action": "subscribe",
                "message": "Subscribed successfully.",
            }
        elif action == "unsubscribe":
            request.user.subscribed_to.remove(subscribe_to)
            return {
                "action": "unsubscribe",
                "message": "Unsubscribed successfully.",
            }


def can_edit(obj, minutes_to_edit=5):
    """Returns True if Post/Comment was created less than 'minutes_to_edit'
    minutes ago"""
    return django_timezone.now() - obj.created_at < timedelta(
        minutes=minutes_to_edit
    )


class EditableValidator:
    def __call__(self, value):
        if not can_edit(value):
            raise serializers.ValidationError("Cannot edit after 5 minutes")


class RestrictUpdateMixin:
    def update(self, instance, validated_data):
        """Allow update only for 5 minutes after Comment creation"""
        # Validate if the Comment can be edited
        EditableValidator()(instance)
        return super().update(instance, validated_data)


class CommentSerializer(RestrictUpdateMixin, serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ("id", "created_at", "text", "media", "user", "post")
        read_only_fields = ["user", "post"]


class CommentListSerializer(serializers.ModelSerializer):
    user = UserPostSerializer(read_only=True)
    url = serializers.HyperlinkedIdentityField(
        many=False, view_name="social_media:comment-detail", read_only=True
    )

    class Meta:
        model = Comment
        fields = (
            "id",
            "created_at",
            "text",
            "media",
            "user",
            "likes_count",
            "url",
        )


class PostSerializer(RestrictUpdateMixin, serializers.ModelSerializer):
    class Meta:
        model = Post
        fields = ("id", "created_at", "text", "media", "user")
        read_only_fields = ["user"]


class LikePostSerializer(serializers.Serializer):
    obj = serializers.PrimaryKeyRelatedField(queryset=Post.objects.all())

    class Meta:
        read_only_fields = ["obj"]

    def validate_obj(self, obj):
        request = self.context.get("request")
        action = self.context.get("action")

        user_liked_objects = (
            request.user.liked_posts.all()
            if isinstance(obj, Post)
            else request.user.liked_comments.all()
        )

        if obj in user_liked_objects and action == "like":
            raise serializers.ValidationError("Already liked")
        elif obj not in user_liked_objects and action == "unlike":
            raise serializers.ValidationError("Not liked")

        return obj

    def perform_action(self, obj, request):
        action = self.context.get("action")

        # Check if the post is already liked to determine the action
        if action == "unlike":
            if isinstance(obj, Post):
                request.user.liked_posts.remove(obj)
            else:
                request.user.liked_comments.remove(obj)
            return {"action": "unlike", "message": "Unliked successfully."}
        elif action == "like":
            if isinstance(obj, Post):
                request.user.liked_posts.add(obj)
            else:
                request.user.liked_comments.add(obj)
            return {"action": "like", "message": "Liked successfully."}


class LikeCommentSerializer(LikePostSerializer):
    obj = serializers.PrimaryKeyRelatedField(queryset=Comment.objects.all())


class PostScheduleSerializer(PostSerializer):
    post_date = serializers.DateTimeField()

    class Meta:
        model = Post
        fields = ("id", "created_at", "text", "media", "post_date", "user")
        read_only_fields = ["user"]


class PostListSerializer(PostSerializer):
    user = UserPostSerializer(read_only=True)
    url = serializers.HyperlinkedIdentityField(
        many=False, read_only=True, view_name="social_media:post-detail"
    )

    class Meta:
        model = Post
        fields = (
            "id",
            "created_at",
            "user",
            "text",
            "media",
            "comments_count",
            "likes_count",
            "url",
        )


class UserWithPostsSerializer(serializers.HyperlinkedModelSerializer):
    subscribed_to = UserListSerializer(many=True)
    subscribers = UserListSerializer(many=True)
    posts = serializers.SerializerMethodField()

    class Meta:
        model = get_user_model()
        fields = (
            "id",
            "profile_picture",
            "username",
            "full_name",
            "bio",
            "location",
            "website",
            "subscribers_count",
            "subscribers",
            "subscribed_to",
            "posts",
        )

    def get_posts(self, obj):
        queryset = obj.posts.prefetch_related(
            "users_liked", "comments"
        ).order_by("-created_at")
        return paginate_queryset(
            PostListSerializer, queryset, self.context.get("request")
        )


class CommentDetailSerializer(CommentSerializer):
    user = UserPostSerializer(read_only=True)
    post = PostListSerializer(read_only=True)


class PostDetailSerializer(serializers.HyperlinkedModelSerializer):
    user = UserPostSerializer(read_only=True)
    comments = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = (
            "id",
            "user",
            "created_at",
            "text",
            "media",
            "likes_count",
            "comments",
        )

    def get_comments(self, obj):
        queryset = obj.comments.order_by("-created_at")
        return paginate_queryset(
            CommentListSerializer, queryset, self.context.get("request")
        )


class TaskSerializer:
    """Serializer for parsing data to Celery task in Post's 'schedule'
    endpoint"""

    @staticmethod
    def get_seconds_from_date(post_date: str) -> int:
        """Get number of seconds for Celery task countdown from user input in
        Post's schedule endpoint"""
        date = datetime.fromisoformat(post_date)
        time_delta = date - datetime.now()
        return int(time_delta.total_seconds())

    @staticmethod
    def create_temp_file(media_file: InMemoryUploadedFile = None) -> str:
        """Create temporary file for use in the Celery task"""
        if media_file:
            return default_storage.save(
                f"temp/{media_file.name}", ContentFile(media_file.read())
            )

        return ""

    @staticmethod
    def serialize_task_data(request) -> Dict[str, Any]:
        """Returns dict with serialized data"""
        task_data = {"user_id": request.user.id}

        setattr(request.data, "_mutable", True)

        post_date = request.data.pop("post_date")[0]
        task_data["countdown"] = TaskSerializer.get_seconds_from_date(
            post_date
        )

        media_file = request.data.pop("media")[0]
        task_data["media_path"] = TaskSerializer.create_temp_file(media_file)

        task_data["request_data"] = request.data

        return task_data

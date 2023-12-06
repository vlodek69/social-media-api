from django.contrib.auth import get_user_model
from rest_framework import serializers

from social_media.models import Post, Comment


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


class UserDetailSerializer(UserListSerializer):
    subscribed_to = UserListSerializer(many=True)
    subscribers = UserListSerializer(many=True)

    class Meta:
        model = get_user_model()
        fields = (
            "id",
            "username",
            "full_name",
            "bio",
            "location",
            "website",
            "profile_picture",
            "subscribed_to",
            "subscribers_count",
            "subscribers",
        )


class UserSubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ()


class PostSerializer(serializers.ModelSerializer):
    class Meta:
        model = Post
        fields = ("id", "created_at", "text", "media", "user")
        read_only_fields = ["user"]


class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ("id", "created_at", "text", "media", "user", "post")
        read_only_fields = ["user", "post"]


class CommentListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ("id", "created_at", "text", "media", "user")
        read_only_fields = ["user"]


class PostDetailSerializer(PostSerializer):
    comments = CommentListSerializer(many=True)

    class Meta:
        model = Post
        fields = ("id", "created_at", "text", "media", "user", "comments")
        read_only_fields = ["user", "comments"]

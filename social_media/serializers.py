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


class UserPostSerializer(UserListSerializer):
    class Meta:
        model = get_user_model()
        fields = ("id", "profile_picture", "full_name", "username")


class UserDetailSerializer(UserListSerializer):
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


class UserSubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ()


class CommentSerializer(serializers.ModelSerializer):
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
        fields = ("id", "created_at", "text", "media", "user", "url")


class PostSerializer(serializers.ModelSerializer):
    class Meta:
        model = Post
        fields = ("id", "created_at", "text", "media", "user")
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
            "url",
        )


class CommentDetailSerializer(CommentSerializer):
    user = UserPostSerializer(read_only=True)
    post = PostListSerializer(read_only=True)


class PostDetailSerializer(PostSerializer):
    user = UserPostSerializer(read_only=True)
    comments = CommentListSerializer(many=True)

    class Meta:
        model = Post
        fields = ("id", "user", "created_at", "text", "media", "comments")

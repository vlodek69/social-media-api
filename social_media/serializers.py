from django.contrib.auth import get_user_model
from rest_framework import serializers


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

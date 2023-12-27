import os
import uuid

from django.conf import settings
from django.db import models


def post_file_path(instance, filename) -> str | os.PathLike:
    _, extension = os.path.splitext(filename)
    filename = f"post-{uuid.uuid4()}{extension}"

    return os.path.join(
        "uploads", "users", instance.user.username, "posts", filename
    )


class BasePost(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    text = models.CharField(max_length=144)
    media = models.ImageField(blank=True, upload_to=post_file_path)

    class Meta:
        abstract = True

    @property
    def likes_count(self):
        return self.users_liked.all().count()


class Post(BasePost):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="posts",
    )

    @property
    def comments_count(self):
        return self.comments.all().count()


class Comment(BasePost):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="comments",
    )
    post = models.ForeignKey(
        Post, on_delete=models.CASCADE, related_name="comments"
    )

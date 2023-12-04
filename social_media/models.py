import os
import uuid

from django.contrib.auth import get_user_model
from django.db import models


def post_file_path(instance, filename):
    _, extension = os.path.splitext(filename)
    filename = f"post-{uuid.uuid4()}{extension}"

    return os.path.join(
        f"uploads/users/{instance.user.username}/posts/", filename
    )


class Post(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    text = models.CharField(max_length=144)
    media = models.ImageField(blank=True, upload_to=post_file_path)
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, related_name="posts")

    class Meta:
        ordering = ["-created_at"]

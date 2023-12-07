import os
import uuid

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext as _
from django.forms.models import model_to_dict

from social_media.models import Post, Comment


class UserManager(BaseUserManager):
    """Define a model manager for User model with no username field."""

    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        """Create and save a User with the given email and password."""
        if not email:
            raise ValueError("The given email must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        """Create and save a regular User with the given email and password."""
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        """Create and save a SuperUser with the given email and password."""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(email, password, **extra_fields)


def user_profile_picture_file_path(instance, filename):
    _, extension = os.path.splitext(filename)
    filename = f"{slugify(instance.username)}-{uuid.uuid4()}{extension}"

    return os.path.join(
        f"uploads/users/{instance.username}/profile_picture/", filename
    )


class User(AbstractUser):
    email = models.EmailField(_("email address"), unique=True)
    full_name = models.CharField(blank=True, null=True, max_length=150)
    date_of_birth = models.DateField(null=True)
    bio = models.CharField(max_length=150, blank=True)
    location = models.CharField(max_length=60, blank=True)
    website = models.URLField(max_length=100, blank=True)
    profile_picture = models.ImageField(
        null=True, upload_to=user_profile_picture_file_path
    )
    subscribed_to = models.ManyToManyField(
        "self", blank=True, symmetrical=False
    )
    liked_posts = models.ManyToManyField(
        Post, blank=True, related_name="users_liked"
    )
    liked_comments = models.ManyToManyField(
        Comment, blank=True, related_name="users_liked"
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    @property
    def subscribers(self):
        data = get_user_model().objects.filter(subscribed_to=self)
        serialized_data = [model_to_dict(item) for item in data]
        return serialized_data

    @property
    def subscribers_count(self):
        subscribers = get_user_model().objects.filter(subscribed_to=self)
        return subscribers.count()

# Generated by Django 4.2.7 on 2024-02-18 15:12

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("social_media", "0004_alter_comment_user_alter_post_user"),
    ]

    operations = [
        migrations.AddField(
            model_name="comment",
            name="users_liked",
            field=models.ManyToManyField(
                related_name="liked_%(class)ss", to=settings.AUTH_USER_MODEL
            ),
        ),
        migrations.AddField(
            model_name="post",
            name="users_liked",
            field=models.ManyToManyField(
                related_name="liked_%(class)ss", to=settings.AUTH_USER_MODEL
            ),
        ),
    ]

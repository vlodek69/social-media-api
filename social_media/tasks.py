# Create your tasks here

from social_media.models import Post

from celery import shared_task


@shared_task
def count_posts():
    return Post.objects.all().count()

# Create your tasks here
# celery -A social_media_api worker -l info -P gevent

from celery import shared_task
from django.core.files.base import ContentFile

from django.core.files.storage import default_storage, FileSystemStorage

from social_media.serializers import PostSerializer


def validate_and_save_serializer(serializer, user_id, media_file=None):
    serializer.is_valid(raise_exception=True)
    serializer.save(
        user_id=user_id, media=media_file
    ) if media_file else serializer.save(user_id=user_id)


def open_and_read_file(file_path):
    with default_storage.open(file_path, "rb") as file:
        return ContentFile(file.read(), name=file_path)


@shared_task
def schedule_post_create(user_id, request_data, media_path):
    storage = FileSystemStorage()
    serializer = PostSerializer(data=request_data)

    if media_path:
        media_file = open_and_read_file(media_path)
        validate_and_save_serializer(serializer, user_id, media_file)
        storage.delete(media_path)
    else:
        validate_and_save_serializer(serializer, user_id)

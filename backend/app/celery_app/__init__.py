from celery import Celery
from app.config import settings

celery_app = Celery(
    "learning_space_tasks",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_send_sent_event=True,
)

# Import tasks to register them
from app.celery_app import tasks  # noqa

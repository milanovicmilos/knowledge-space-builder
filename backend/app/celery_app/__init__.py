from celery import Celery
from app.config import settings

celery_app = Celery(
    "learning_space_generator",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

# Import tasks to register them with Celery
from app.celery_app import tasks  # noqa: F401

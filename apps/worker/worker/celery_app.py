"""Celery app. Queues are split by cost (Architecture section 16)."""

import os

from celery import Celery

app = Celery("aitms", broker=os.environ.get("REDIS_URL", "redis://redis:6379/0"))
app.conf.task_default_queue = "eval-light"
app.conf.task_acks_late = True

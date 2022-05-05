
import os
from celery import Celery
# import app.workers.ml
import app.workers.recorder

os.environ.setdefault('CELERY_CONFIG_MODULE', 'app.workers.celery_config')

app = Celery()
app.config_from_envvar('CELERY_CONFIG_MODULE')
app.Task.track_started = True  # lets us know if a task is currently running
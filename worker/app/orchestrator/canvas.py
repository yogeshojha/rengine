"""The scan canvas bound to the worker's celery app."""

from functools import partial

from app.celery import celery_app
from shared.services.orchestrator import canvas

build_canvas = partial(canvas.build_canvas, celery_app)
build_step = partial(canvas.build_step, celery_app)

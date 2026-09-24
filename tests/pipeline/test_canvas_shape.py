from __future__ import annotations

import json

import pytest
from celery import Celery, chord

from shared.definitions.constants import SCAN_CONTROL_QUEUE, SCANS_QUEUE
from shared.services.orchestrator import canvas

pytestmark = pytest.mark.pipeline

MESSAGE_CAP = 4096


@pytest.fixture(scope="module")
def app() -> Celery:
    return Celery("canvas-test", broker="memory://", set_as_current=False)


def _size(obj) -> int:
    return len(json.dumps(obj))


def _messages(step) -> list[int]:
    """What each header task of a step carries once the chord body is attached."""
    if isinstance(step, chord):
        body = _size(step.body)
        return [_size(sig) + body for sig in step.tasks]
    first, *rest = step.tasks
    return [_size(first) + sum(_size(sig) for sig in rest)]


def test_every_stage_message_stays_small(app: Celery):
    steps = canvas.plan_steps()
    for index in range(len(steps)):
        for size in _messages(canvas.build_step(app, "s1", 0, steps, index)):
            assert size < MESSAGE_CAP


def test_a_step_hands_over_to_the_next_step_not_to_the_rest_of_the_plan(app: Celery):
    steps = canvas.plan_steps()
    first = canvas.build_canvas(app, "s1", 0)
    assert isinstance(first, chord)
    assert first.body.task == canvas.STEP_TASK
    assert first.body.kwargs == {
        "scan_id": "s1",
        "epoch": 0,
        "steps": steps,
        "index": 1,
    }


def test_the_last_step_hands_over_to_finalize(app: Celery):
    steps = canvas.plan_steps()
    last = canvas.build_step(app, "s1", 2, steps, len(steps) - 1)
    after = last.body if isinstance(last, chord) else last.tasks[-1]
    assert after.task == canvas.FINALIZE_TASK
    assert after.kwargs == {"scan_id": "s1", "epoch": 2}


def test_a_step_past_the_plan_is_finalize(app: Celery):
    sig = canvas.build_step(app, "s1", 0, [["http_probe"]], 5)
    assert sig.task == canvas.FINALIZE_TASK


def test_a_resume_carries_only_the_steps_left(app: Celery):
    full = canvas.plan_steps()
    done = set(full[0])
    left = canvas.plan_steps(1, done)
    assert left == full[1:]
    first = canvas.build_canvas(app, "s1", 1, start_level=1, done=done)
    assert first.body.kwargs["steps"] == left


def test_every_stage_carries_finalize_as_its_error_link(app: Celery):
    first = canvas.build_canvas(app, "s1", 0)
    for sig in first.tasks:
        (link,) = sig.options["link_error"]
        assert link.task == canvas.FINALIZE_TASK
        assert set(sig.options) == {"queue", "link_error"}


def test_stages_queue_for_a_stage_slot_and_hand_overs_do_not(app: Celery):
    steps = canvas.plan_steps()
    for index in range(len(steps)):
        step = canvas.build_step(app, "s1", 0, steps, index)
        stages = step.tasks if isinstance(step, chord) else step.tasks[:-1]
        after = step.body if isinstance(step, chord) else step.tasks[-1]
        for sig in stages:
            assert sig.options["queue"] == SCANS_QUEUE
            (link,) = sig.options["link_error"]
            assert link.options["queue"] == SCAN_CONTROL_QUEUE
        assert after.options["queue"] == SCAN_CONTROL_QUEUE

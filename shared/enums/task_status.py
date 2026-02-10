from enum import Enum


class TaskStatus(Enum):
    PENDING = "pending"
    QUERYING = "querying"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    NOT_APPLICABLE = "not_applicable"

"""The canvas generation a scan task belongs to."""


def superseded(scan_epoch: int | None, task_epoch: int | None) -> bool:
    """True when the scan has moved past the canvas this task was queued for."""
    if task_epoch is None:
        return False
    return (scan_epoch or 0) != task_epoch

from pathlib import Path


def purge_dir(root: str, item_id: object) -> None:
    """Delete root/<item_id> and the files in it."""
    directory = Path(root) / str(item_id)
    if not directory.exists():
        return
    for item in directory.iterdir():
        item.unlink(missing_ok=True)
    directory.rmdir()

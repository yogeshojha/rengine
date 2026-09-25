import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Column, PrimaryKeyConstraint
from sqlmodel import Field, SQLModel


class ScanRevision(SQLModel, table=True):
    """Change counters per scan and dimension, bumped by triggers on the result tables."""

    __tablename__ = "scan_revisions"
    __table_args__ = (PrimaryKeyConstraint("scan_id", "dimension"),)

    scan_id: uuid.UUID = Field(foreign_key="scans.id", ondelete="CASCADE")
    dimension: str = Field(max_length=32)
    # the scan's own rows
    rows_rev: int = Field(default=0, sa_column=Column(BigInteger, nullable=False))
    # the scan's own rows or an earlier row of its target
    history_rev: int = Field(default=0, sa_column=Column(BigInteger, nullable=False))


class ScanDelta(SQLModel, table=True):
    """A scan's rows and the keys it was the first to report for its target, as of `history_rev`."""

    __tablename__ = "scan_deltas"
    __table_args__ = (PrimaryKeyConstraint("scan_id", "dimension"),)

    scan_id: uuid.UUID = Field(foreign_key="scans.id", ondelete="CASCADE")
    dimension: str = Field(max_length=32)
    history_rev: int = Field(sa_column=Column(BigInteger, nullable=False))
    first_seen: int
    rows: int
    first_at: datetime | None = None


class ScanRetired(SQLModel, table=True):
    """Keys the previous run held that a scan lacks, as of both runs' `rows_rev`."""

    __tablename__ = "scan_retired"
    __table_args__ = (PrimaryKeyConstraint("scan_id", "prev_scan_id", "dimension"),)

    scan_id: uuid.UUID = Field(foreign_key="scans.id", ondelete="CASCADE")
    prev_scan_id: uuid.UUID = Field(foreign_key="scans.id", ondelete="CASCADE")
    dimension: str = Field(max_length=32)
    rows_rev: int = Field(sa_column=Column(BigInteger, nullable=False))
    prev_rows_rev: int = Field(sa_column=Column(BigInteger, nullable=False))
    retired: int

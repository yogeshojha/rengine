"""The scan surface plan: what a vulnerability scanner is handed, and why."""

from shared.services.scan_surface.batches import batch_size, batches, chunk
from shared.services.scan_surface.cluster import (
    RootCandidate,
    cluster_roots,
    same_origin,
)
from shared.services.scan_surface.normalize import (
    parse_root,
    root_value,
    service_value,
)
from shared.services.scan_surface.plan import (
    SurfaceItem,
    SurfacePlan,
    build,
    mark,
    settle,
    split_members,
    write,
)
from shared.services.scan_surface.rank import base_rank, cluster_rank
from shared.services.scan_surface.requests import build_requests, by_origin
from shared.services.scan_surface.tech import host_tags
from shared.services.scan_surface.tiers import (
    TierPlan,
    cost,
    split,
    tech_groups,
    wants_callback,
)

__all__ = [
    "RootCandidate",
    "SurfaceItem",
    "SurfacePlan",
    "TierPlan",
    "base_rank",
    "batch_size",
    "batches",
    "build",
    "build_requests",
    "by_origin",
    "chunk",
    "cluster_rank",
    "cluster_roots",
    "cost",
    "host_tags",
    "mark",
    "parse_root",
    "root_value",
    "same_origin",
    "service_value",
    "settle",
    "split",
    "split_members",
    "tech_groups",
    "wants_callback",
    "write",
]

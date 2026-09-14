"""The scan surface plan: what a vulnerability scanner is handed, and why."""

from shared.services.scan_surface.batches import batch_size, batches, chunk
from shared.services.scan_surface.cluster import (
    Cluster,
    RootCandidate,
    cluster_roots,
    same_origin,
)
from shared.services.scan_surface.normalize import (
    Root,
    parse_root,
    root_value,
    service_value,
)
from shared.services.scan_surface.plan import (
    SurfaceItem,
    SurfacePlan,
    build,
    covered_before,
    library_tags,
    mark,
    settle,
    split_members,
    write,
)
from shared.services.scan_surface.rank import base_rank, cluster_rank
from shared.services.scan_surface.requests import (
    FUZZABLE_CLASSES,
    Origin,
    build_requests,
    by_origin,
    origins,
)
from shared.services.scan_surface.tech import host_tags
from shared.services.scan_surface.tiers import (
    TechGroup,
    TierPlan,
    cost,
    split,
    tech_groups,
    top_paths,
)

__all__ = [
    "FUZZABLE_CLASSES",
    "Cluster",
    "Origin",
    "Root",
    "RootCandidate",
    "SurfaceItem",
    "SurfacePlan",
    "TechGroup",
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
    "covered_before",
    "host_tags",
    "library_tags",
    "mark",
    "origins",
    "parse_root",
    "root_value",
    "same_origin",
    "service_value",
    "settle",
    "split",
    "split_members",
    "tech_groups",
    "top_paths",
    "write",
]

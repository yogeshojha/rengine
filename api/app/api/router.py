from fastapi import APIRouter

from app.api.v1 import (
    activity_logs,
    api_keys,
    auth,
    celery_health,
    events,
    notifications,
    organizations,
    projects,
    ripestat,
    tags,
    targets,
    users,
    viewdns,
    whois,
)

router = APIRouter()

router.include_router(auth.router)
router.include_router(users.router)
router.include_router(events.router)
router.include_router(projects.router)
router.include_router(organizations.router)
router.include_router(targets.router)
router.include_router(tags.router)
router.include_router(activity_logs.router)
router.include_router(notifications.router)
router.include_router(api_keys.router)
router.include_router(whois.router)
router.include_router(viewdns.router)
router.include_router(ripestat.router)
router.include_router(celery_health.router)

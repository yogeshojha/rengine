from fastapi import APIRouter

from app.api.v1 import (
    activity_logs,
    api_keys,
    auth,
    celery_health,
    dashboard,
    events,
    instance_settings,
    notification_channels,
    notifications,
    onboarding,
    organizations,
    projects,
    proxies,
    ripestat,
    scan_contexts,
    scan_engines,
    scan_schedules,
    scans,
    subdomains,
    tags,
    targets,
    totp,
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
router.include_router(scan_engines.router)
router.include_router(scan_contexts.router)
router.include_router(scan_schedules.router)
router.include_router(scans.router)
router.include_router(subdomains.router)
router.include_router(dashboard.router)
router.include_router(celery_health.router)
router.include_router(instance_settings.router)
router.include_router(proxies.router)
router.include_router(notification_channels.router)
router.include_router(onboarding.router)
router.include_router(totp.router)

import shared.models._tztypes  # patch datetime->timestamptz first
from shared.models.activity_log import ActivityLog
from shared.models.ai import AiCall, AiConnection, AiNarrative
from shared.models.api_key import APIKey
from shared.models.ask import AskMessage, AskThread
from shared.models.cloud_storage import CloudBucket, CloudBucketTriage
from shared.models.connector import (
    Connector,
    ConnectorAction,
    ConnectorCandidate,
    ConnectorHost,
)
from shared.models.dns import DnsLookup, DnsRecord
from shared.models.domain_posture import DomainPosture
from shared.models.endpoint import Endpoint, EndpointCoverage
from shared.models.estate import EstateCandidate, EstateTriage
from shared.models.export import Export
from shared.models.http_asset import HttpAsset
from shared.models.infostealer import InfostealerLogin, TargetInfostealer
from shared.models.instance_settings import InstanceSettings
from shared.models.interest import InterestDismissal, InterestRule, InterestSignal
from shared.models.ip_address import IpAddress
from shared.models.ip_asn_range import IpAsnRange, IpCountryRange
from shared.models.issue_tracker import (
    IssueTracker,
    IssueTrackerRoute,
    TrackedIssue,
    TrackedIssueComment,
    TrackedIssueFinding,
)
from shared.models.lookalike import LookalikeDomain, LookalikeTriage
from shared.models.note import Note
from shared.models.notification import Notification, NotificationReceipt
from shared.models.notification_channel import NotificationChannel
from shared.models.organization import Organization, OrganizationSummary
from shared.models.port import Port
from shared.models.project import Project
from shared.models.proxy import Proxy
from shared.models.report import Report, ReportFont, ReportTemplate, ReportTheme
from shared.models.ripestat import (
    RIPEStatAbuseContact,
    RIPEStatAnnouncedPrefix,
    RIPEStatASNNeighbour,
    RIPEStatASOverview,
    RIPEStatNetworkInfo,
    RIPEStatPrefixOverview,
    RIPEStatRelatedPrefix,
)
from shared.models.scan import Scan
from shared.models.scan_activity import ScanActivity
from shared.models.scan_command import ScanCommand
from shared.models.scan_context import ScanContext
from shared.models.scan_delta import ScanDelta, ScanRetired, ScanRevision
from shared.models.scan_engine import ScanEngine
from shared.models.scan_schedule import ScanSchedule
from shared.models.scan_surface import ScanSurfaceItem
from shared.models.secret import Secret, SecretCoverage, SecretSighting
from shared.models.software import NvdCpeMatch, NvdCve, SoftwareCve
from shared.models.subdomain import Subdomain
from shared.models.tag import Tag, TagSummary
from shared.models.target import (
    Target,
    TargetBulkCreate,
    TargetBulkCreateResponse,
    TargetCreate,
    TargetImportItem,
    TargetImportRequest,
    TargetImportResult,
    TargetRead,
    TargetType,
    TargetUpdate,
    TargetValidationRequest,
    TargetValidationResponse,
)
from shared.models.target_seed import (
    TargetSeed,
    TargetSeedRead,
    TargetSeedResult,
    TargetSeedWrite,
)
from shared.models.tripwire import Tripwire, TripwireMark, TripwireRun
from shared.models.user import User
from shared.models.viewdns import ViewDNSCache
from shared.models.vuln_template import VulnTemplate
from shared.models.vulnerability import (
    Vulnerability,
    VulnerabilityCoverage,
    VulnerabilityTriage,
)
from shared.models.watch import ProgramWatch, UserMark, WatchEvent, WatchHost
from shared.models.wordlist import Wordlist

TargetRead.model_rebuild()

__all__ = [
    "APIKey",
    "ActivityLog",
    "AiCall",
    "AiConnection",
    "AiNarrative",
    "AskMessage",
    "AskThread",
    "CloudBucket",
    "CloudBucketTriage",
    "Connector",
    "ConnectorAction",
    "ConnectorCandidate",
    "ConnectorHost",
    "DnsLookup",
    "DnsRecord",
    "DomainPosture",
    "Endpoint",
    "EndpointCoverage",
    "EstateCandidate",
    "EstateTriage",
    "Export",
    "HttpAsset",
    "InfostealerLogin",
    "InstanceSettings",
    "InterestDismissal",
    "InterestRule",
    "InterestSignal",
    "IpAddress",
    "IpAsnRange",
    "IpCountryRange",
    "IssueTracker",
    "IssueTrackerRoute",
    "LookalikeDomain",
    "LookalikeTriage",
    "Note",
    "Notification",
    "NotificationChannel",
    "NotificationReceipt",
    "NvdCpeMatch",
    "NvdCve",
    "Organization",
    "OrganizationSummary",
    "Port",
    "ProgramWatch",
    "Project",
    "Proxy",
    "RIPEStatASNNeighbour",
    "RIPEStatASOverview",
    "RIPEStatAbuseContact",
    "RIPEStatAnnouncedPrefix",
    "RIPEStatNetworkInfo",
    "RIPEStatPrefixOverview",
    "RIPEStatRelatedPrefix",
    "Report",
    "ReportFont",
    "ReportTemplate",
    "ReportTheme",
    "Scan",
    "ScanActivity",
    "ScanCommand",
    "ScanContext",
    "ScanDelta",
    "ScanEngine",
    "ScanRetired",
    "ScanRevision",
    "ScanSchedule",
    "ScanSurfaceItem",
    "Secret",
    "SecretCoverage",
    "SecretSighting",
    "SoftwareCve",
    "Subdomain",
    "Tag",
    "TagSummary",
    "Target",
    "TargetBulkCreate",
    "TargetBulkCreateResponse",
    "TargetCreate",
    "TargetImportItem",
    "TargetImportRequest",
    "TargetImportResult",
    "TargetInfostealer",
    "TargetRead",
    "TargetSeed",
    "TargetSeedRead",
    "TargetSeedResult",
    "TargetSeedWrite",
    "TargetType",
    "TargetUpdate",
    "TargetValidationRequest",
    "TargetValidationResponse",
    "TrackedIssue",
    "TrackedIssueComment",
    "TrackedIssueFinding",
    "Tripwire",
    "TripwireMark",
    "TripwireRun",
    "User",
    "UserMark",
    "ViewDNSCache",
    "VulnTemplate",
    "Vulnerability",
    "VulnerabilityCoverage",
    "VulnerabilityTriage",
    "WatchEvent",
    "WatchHost",
    "Wordlist",
]

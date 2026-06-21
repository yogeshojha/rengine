from enum import Enum


class InstanceMode(Enum):
    BUG_BOUNTY = "bug_bounty"
    CORPORATE = "corporate"


class AIProvider(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    AZURE_OPENAI = "azure_openai"
    GOOGLE = "google"

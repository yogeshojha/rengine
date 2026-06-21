from enum import Enum


class NotificationProvider(Enum):
    SLACK = "slack"
    DISCORD = "discord"
    TELEGRAM = "telegram"
    TEAMS = "teams"
    EMAIL = "email"
    WEBHOOK = "webhook"
    CUSTOM = "custom"

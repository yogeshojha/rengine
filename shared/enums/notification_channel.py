from enum import Enum


class NotificationProvider(Enum):
    SLACK = "slack"
    DISCORD = "discord"
    TELEGRAM = "telegram"
    TEAMS = "teams"
    EMAIL = "email"
    WEBHOOK = "webhook"
    CUSTOM = "custom"


DIRECT_POST_PROVIDERS: frozenset[str] = frozenset(
    {NotificationProvider.WEBHOOK.value, NotificationProvider.TEAMS.value}
)

URL_PROVIDERS: frozenset[str] = frozenset(
    {
        NotificationProvider.SLACK.value,
        NotificationProvider.DISCORD.value,
        NotificationProvider.TEAMS.value,
        NotificationProvider.WEBHOOK.value,
    }
)

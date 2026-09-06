from enum import Enum


class NotificationProvider(Enum):
    SLACK = "slack"
    DISCORD = "discord"
    TELEGRAM = "telegram"
    TEAMS = "teams"
    EMAIL = "email"
    WEBHOOK = "webhook"
    CUSTOM = "custom"


# providers whose message is posted straight to a URL the user supplies; every one of
# them must have that URL validated, because an unvalidated one is a request we make
DIRECT_POST_PROVIDERS: frozenset[str] = frozenset(
    {NotificationProvider.WEBHOOK.value, NotificationProvider.TEAMS.value}
)

# providers that carry a user-supplied URL at all, whether or not it is posted directly
URL_PROVIDERS: frozenset[str] = frozenset(
    {
        NotificationProvider.SLACK.value,
        NotificationProvider.DISCORD.value,
        NotificationProvider.TEAMS.value,
        NotificationProvider.WEBHOOK.value,
    }
)

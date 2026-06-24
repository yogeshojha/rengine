import re

TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
MAX_INTERVAL = 100000
MAX_SCHEDULE_TARGETS = 500

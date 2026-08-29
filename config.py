import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

OWNER_ID = 8413337840

ADMIN_IDS = {
    OWNER_ID,
    *{
        int(x.strip())
        for x in os.getenv("ADMIN_IDS", "").split(",")
        if x.strip().isdigit()
    },
}

FREE_USERNAMES = {
    "fragomelov",
    "arhangelovgod",
}

DATABASE_PATH = os.getenv("DATABASE_PATH", "osint_core.db")

DEFAULT_CREDITS = int(os.getenv("DEFAULT_CREDITS", "0"))

REPORT_EXPIRE_HOURS = int(
    os.getenv("REPORT_EXPIRE_HOURS", "24")
)

API_BASE_URL = os.getenv(
    "API_BASE_URL",
    ""
).rstrip("/")

API_SECRET = os.getenv(
    "API_SECRET",
    ""
).strip()

CORS_ORIGINS = [
    x.strip()
    for x in os.getenv(
        "CORS_ORIGINS",
        ""
    ).split(",")
    if x.strip()
]

PROXY_ENABLED = (
    os.getenv(
        "PROXY_ENABLED",
        "false"
    ).lower()
    == "true"
)

LOG_LEVEL = os.getenv(
    "LOG_LEVEL",
    "INFO"
)

HIBP_API_KEY = os.getenv(
    "HIBP_API_KEY",
    ""
).strip()

STARS_20 = int(
    os.getenv("STARS_20", "50")
)

STARS_50 = int(
    os.getenv("STARS_50", "100")
)

STARS_100 = int(
    os.getenv("STARS_100", "150")
)

from pathlib import Path

APP_NAME = "Community Golf Club Manager"
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
EXPORT_DIR = BASE_DIR / "exports"
DB_PATH = DATA_DIR / "golf_club.db"

RSVP_SERVER_HOST = "127.0.0.1"
RSVP_SERVER_PORT = 8081
RSVP_TOKEN_SECRET = "change-me-for-production"

DEFAULT_START_TIME = "10:00"
DEFAULT_TEE_INTERVAL = 9
DEFAULT_GROUP_SIZE = 4
DEFAULT_TEE_TIME_COUNT = 4
DEFAULT_PLAY_DAYS = ["Monday", "Thursday"]

ROLE_ADMIN = "admin"
ROLE_MEMBER = "member"

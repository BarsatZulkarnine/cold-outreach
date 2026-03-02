import os
from dotenv import load_dotenv

load_dotenv()

# Anthropic
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# Google
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")

# Hunter.io
HUNTER_API_KEY = os.getenv("HUNTER_API_KEY", "")

# Gmail OAuth
GMAIL_CREDENTIALS_PATH = os.getenv("GMAIL_CREDENTIALS_PATH", "credentials.json")
GMAIL_TOKEN_PATH = os.getenv("GMAIL_TOKEN_PATH", "gmail_token.json")

# LinkedIn
LINKEDIN_EMAIL = os.getenv("LINKEDIN_EMAIL", "")
LINKEDIN_PASSWORD = os.getenv("LINKEDIN_PASSWORD", "")
LINKEDIN_HEADLESS = os.getenv("LINKEDIN_HEADLESS", "false").lower() == "true"
LINKEDIN_COOKIES_PATH = os.getenv("LINKEDIN_COOKIES_PATH", "linkedin_cookies.json")

# Database
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./outreach.db")

# App
BACKEND_PORT = int(os.getenv("BACKEND_PORT", "8001"))
FRONTEND_PORT = int(os.getenv("FRONTEND_PORT", "5174"))

# Sending limits
MAX_EMAILS_PER_DAY = int(os.getenv("MAX_EMAILS_PER_DAY", "40"))
MAX_CONNECTION_REQUESTS_PER_DAY = int(os.getenv("MAX_CONNECTION_REQUESTS_PER_DAY", "15"))
MAX_DMS_PER_DAY = int(os.getenv("MAX_DMS_PER_DAY", "10"))

# LinkedIn scraper hard limits
MAX_PROFILES_PER_SESSION = 5
MAX_SEARCHES_PER_DAY = 3
MIN_DELAY_BETWEEN_ACTIONS_SEC = 180
MAX_DELAY_BETWEEN_ACTIONS_SEC = 420

# LinkedIn sender delays
MIN_DELAY_BETWEEN_SENDS_SEC = 120
MAX_DELAY_BETWEEN_SENDS_SEC = 300

# Default Google Maps queries for Melbourne tech scene.
# Suburb-specific queries use tighter GPS bias toward that suburb (see maps_scraper.py).
# Generic "Melbourne" queries use a broad 30km radius from CBD.
DEFAULT_MAPS_QUERIES = [
    # Generic — broad Melbourne sweep
    "software company Melbourne VIC",
    "IT company Melbourne",
    "tech startup Melbourne",
    "SaaS company Melbourne",
    "software agency Melbourne",
    # Inner-east tech corridor
    "software development company Cremorne Melbourne",
    "software development company Richmond Melbourne",
    "software development company Collingwood Melbourne",
    "tech company Fitzroy Melbourne",
    "software company Abbotsford Melbourne",
    # Inner-north
    "software company Northcote Melbourne",
    "tech company Brunswick Melbourne",
    "software company Carlton Melbourne",
    # Inner-south / south-east
    "software company South Melbourne",
    "tech company Southbank Melbourne",
    "software company Prahran Melbourne",
    "software company South Yarra Melbourne",
    "software company Hawthorn Melbourne",
    # West / Docklands
    "tech company Docklands Melbourne",
    # East
    "software company Box Hill Melbourne",
]

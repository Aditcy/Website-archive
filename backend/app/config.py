import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    app = os.getenv("APP_NAME", "Website Archive")

    db = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://localhost/website_archive",
    )

    redis = os.getenv(
        "REDIS_URL",
        "redis://127.0.0.1:6379/0",
    )

    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))

    workers = int(os.getenv("CRAWL_WORKERS", "2"))
    batch = int(os.getenv("CRAWL_BATCH", "100"))
    timeout = float(os.getenv("HTTP_TIMEOUT", "20"))
    retries = int(os.getenv("MAX_RETRIES", "3"))
    delay = float(os.getenv("DOMAIN_DELAY", "1"))

    # Maximum number of URLs processed by one crawl.
    max_urls = int(os.getenv("MAX_URLS", "1000"))

    auto_submit = os.getenv("AUTO_SUBMIT", "false").lower() == "true"
    archive_service = os.getenv("ARCHIVE_SERVICE", "wayback")

    user_agent = os.getenv(
        "USER_AGENT",
        "WebsiteArchiveBot/1.0",
    )

    ia_key = os.getenv("IA_KEY", "")
    ia_secret = os.getenv("IA_SECRET", "")


cfg = Settings()

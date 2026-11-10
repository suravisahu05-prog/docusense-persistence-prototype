import os
from dataclasses import dataclass
from dotenv import load_dotenv
load_dotenv()

@dataclass(frozen=True)
class Settings:
    cors_origins: list[str]
    max_upload_mb: int = int(os.getenv("MAX_UPLOAD_MB", "25"))
    temp_dir: str = os.getenv("TEMP_DIR", "var/uploads")

settings = Settings(cors_origins=[
    x.strip() for x in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:3000,http://localhost:5173,http://127.0.0.1:5173"
    ).split(",") if x.strip()
])
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}

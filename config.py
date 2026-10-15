import os
from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Load environment variables from .env file if it exists locally
load_dotenv(os.path.join(BASE_DIR, '.env'))

# Detect if running in Vercel / AWS Lambda serverless environment
IS_VERCEL = bool(os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "techeasy-engineering-maths-super-secret-key-2026")
    
    # On Vercel, default to 'mysql' to connect to cloud database and avoid read-only SQLite errors
    default_db_type = "mysql" if IS_VERCEL else "sqlite"
    DATABASE_TYPE = os.environ.get("DB_TYPE", default_db_type).lower().strip()
    
    # SQLite configuration (use /tmp on Vercel if SQLite is ever used)
    SQLITE_PATH = "/tmp/engineering_maths.db" if IS_VERCEL else os.path.join(BASE_DIR, "engineering_maths.db")
    
    # Cloud MySQL configuration (read from environment variables / .env)
    MYSQL_HOST = os.environ.get("MYSQL_HOST", "localhost")
    MYSQL_PORT = int(os.environ.get("MYSQL_PORT", 3306))
    MYSQL_USER = os.environ.get("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "")
    MYSQL_DB = os.environ.get("MYSQL_DB", "defaultdb")
    MYSQL_SSL = os.environ.get("MYSQL_SSL", "true").lower().strip() in ("true", "1", "yes")
    
    # Upload folder for question and option images (use /tmp on Vercel read-only filesystem)
    UPLOAD_FOLDER = "/tmp/uploads/questions" if IS_VERCEL else os.path.join(BASE_DIR, "uploads", "questions")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max upload
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}

import os
from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Load environment variables from .env file if it exists
load_dotenv(os.path.join(BASE_DIR, '.env'))

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "techeasy-engineering-maths-super-secret-key-2026")
    DATABASE_TYPE = os.environ.get("DB_TYPE", "sqlite").lower().strip()  # 'sqlite' or 'mysql'
    
    # SQLite configuration
    SQLITE_PATH = os.path.join(BASE_DIR, "engineering_maths.db")
    
    # MySQL configuration (Cloud MySQL: TiDB Cloud, Aiven, PlanetScale, Railway, AWS RDS)
    MYSQL_HOST = os.environ.get("MYSQL_HOST", "localhost")
    MYSQL_PORT = int(os.environ.get("MYSQL_PORT", 3306))
    MYSQL_USER = os.environ.get("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "")
    MYSQL_DB = os.environ.get("MYSQL_DB", "engineering_maths")
    MYSQL_SSL = os.environ.get("MYSQL_SSL", "true").lower().strip() in ("true", "1", "yes")
    
    # Upload folder for question and option images
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads", "questions")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max upload
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}

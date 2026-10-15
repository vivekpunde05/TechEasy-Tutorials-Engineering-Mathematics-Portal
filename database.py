import sqlite3
import re
from flask import g, current_app
from config import Config

def get_db():
    """Get or create the database connection (SQLite or Cloud MySQL). Works both in and out of Flask request context."""
    from flask import has_app_context
    use_mysql = (Config.DATABASE_TYPE == 'mysql')

    if use_mysql:
        import pymysql
        kwargs = {
            'host': Config.MYSQL_HOST,
            'port': Config.MYSQL_PORT,
            'user': Config.MYSQL_USER,
            'password': Config.MYSQL_PASSWORD,
            'database': Config.MYSQL_DB,
            'cursorclass': pymysql.cursors.DictCursor,
            'autocommit': False,
            'charset': 'utf8mb4'
        }
        if Config.MYSQL_SSL:
            kwargs['ssl'] = {'ssl': True}

        if has_app_context():
            if 'db' not in g:
                g.db = pymysql.connect(**kwargs)
            return g.db
        else:
            return pymysql.connect(**kwargs)
    else:
        if has_app_context():
            if 'db' not in g:
                g.db = sqlite3.connect(Config.SQLITE_PATH)
                g.db.row_factory = sqlite3.Row
                g.db.execute("PRAGMA foreign_keys = ON;")
            return g.db
        else:
            conn = sqlite3.connect(Config.SQLITE_PATH)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON;")
            return conn

def close_db(e=None):
    """Close the database connection at the end of the request."""
    db = g.pop('db', None)
    if db is not None:
        db.close()
def _format_query(query):
    """Format queries for database dialect compatibility."""
    if Config.DATABASE_TYPE == 'mysql':
        # 1. Parameter substitution
        formatted = query.replace('?', '%s')
        # 2. Syntax compatibility
        formatted = re.sub(r'INSERT\s+OR\s+REPLACE\s+INTO', 'REPLACE INTO', formatted, flags=re.IGNORECASE)
        formatted = re.sub(r'INSERT\s+OR\s+IGNORE\s+INTO', 'INSERT IGNORE INTO', formatted, flags=re.IGNORECASE)
        return formatted
    return query

def query_db(query, args=(), one=False):
    """Execute a SELECT query and return rows as dictionary-like objects."""
    db = get_db()
    if Config.DATABASE_TYPE == 'mysql':
        formatted_query = _format_query(query)
        cur = db.cursor()
        cur.execute(formatted_query, args)
        rv = cur.fetchall()
        cur.close()
        if one:
            return dict(rv[0]) if rv else None
        return [dict(row) for row in rv]
    else:
        cur = db.execute(query, args)
        rv = cur.fetchall()
        cur.close()
        if one:
            return dict(rv[0]) if rv else None
        return [dict(row) for row in rv]

def execute_db(query, args=(), commit=True):
    """Execute INSERT/UPDATE/DELETE query and return lastrowid and rowcount."""
    db = get_db()
    if Config.DATABASE_TYPE == 'mysql':
        formatted_query = _format_query(query)
        cur = db.cursor()
        cur.execute(formatted_query, args)
        if commit:
            db.commit()
        last_id = cur.lastrowid
        rowcount = cur.rowcount
        cur.close()
        return last_id, rowcount
    else:
        cur = db.execute(query, args)
        if commit:
            db.commit()
        last_id = cur.lastrowid
        rowcount = cur.rowcount
        cur.close()
        return last_id, rowcount

def init_db():
    """Initialize database tables if they do not exist (supports SQLite & MySQL)."""
    db = get_db()

    if Config.DATABASE_TYPE == 'mysql':
        cursor = db.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            email VARCHAR(255) UNIQUE NOT NULL,
            mobile VARCHAR(50) NOT NULL,
            password VARCHAR(255) NOT NULL,
            role VARCHAR(50) NOT NULL DEFAULT 'student',
            course_type VARCHAR(50) DEFAULT 'Degree',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS subjects (
            id INT AUTO_INCREMENT PRIMARY KEY,
            course_type VARCHAR(50) NOT NULL,
            semester VARCHAR(50) NOT NULL,
            subject_name VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS chapters (
            id INT AUTO_INCREMENT PRIMARY KEY,
            subject_id INT NOT NULL,
            chapter_name VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS topics (
            id INT AUTO_INCREMENT PRIMARY KEY,
            chapter_id INT NOT NULL,
            topic_name VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (chapter_id) REFERENCES chapters(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS questions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            subject_id INT NOT NULL,
            chapter_id INT NOT NULL,
            question TEXT NOT NULL,
            question_image VARCHAR(255) DEFAULT '',
            option_a TEXT NOT NULL,
            option_a_image VARCHAR(255) DEFAULT '',
            option_b TEXT NOT NULL,
            option_b_image VARCHAR(255) DEFAULT '',
            option_c TEXT NOT NULL,
            option_c_image VARCHAR(255) DEFAULT '',
            option_d TEXT NOT NULL,
            option_d_image VARCHAR(255) DEFAULT '',
            correct_answer VARCHAR(10) NOT NULL,
            explanation TEXT,
            explanation_image VARCHAR(255) DEFAULT '',
            difficulty VARCHAR(50) DEFAULT 'Medium',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE,
            FOREIGN KEY (chapter_id) REFERENCES chapters(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS tests (
            id INT AUTO_INCREMENT PRIMARY KEY,
            test_name VARCHAR(255) NOT NULL,
            course_type VARCHAR(50) NOT NULL,
            subject_id INT NOT NULL,
            number_of_questions INT DEFAULT 0,
            time_limit INT NOT NULL DEFAULT 30,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS test_questions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            test_id INT NOT NULL,
            question_id INT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (test_id) REFERENCES tests(id) ON DELETE CASCADE,
            FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE,
            UNIQUE KEY unique_test_q (test_id, question_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS attempts (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            test_id INT NOT NULL,
            score INT NOT NULL DEFAULT 0,
            total_questions INT NOT NULL DEFAULT 0,
            percentage DOUBLE NOT NULL DEFAULT 0.0,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (test_id) REFERENCES tests(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS attempt_answers (
            id INT AUTO_INCREMENT PRIMARY KEY,
            attempt_id INT NOT NULL,
            question_id INT NOT NULL,
            selected_answer VARCHAR(10) DEFAULT '',
            is_correct INT DEFAULT 0,
            FOREIGN KEY (attempt_id) REFERENCES attempts(id) ON DELETE CASCADE,
            FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS test_results (
            id INT AUTO_INCREMENT PRIMARY KEY,
            student_id INT NOT NULL,
            subject_id INT NOT NULL,
            chapter_id INT,
            total_questions INT NOT NULL DEFAULT 0,
            correct_answers INT NOT NULL DEFAULT 0,
            wrong_answers INT NOT NULL DEFAULT 0,
            score INT NOT NULL DEFAULT 0,
            percentage DOUBLE NOT NULL DEFAULT 0.0,
            test_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE,
            FOREIGN KEY (chapter_id) REFERENCES chapters(id) ON DELETE SET NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS video_lectures (
            id INT AUTO_INCREMENT PRIMARY KEY,
            course_type VARCHAR(50) NOT NULL,
            youtube_link TEXT NOT NULL,
            description TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        # Ensure default admin account exists
        from werkzeug.security import generate_password_hash
        cursor.execute("SELECT id FROM users WHERE email = %s", ("admin@techeasy.com",))
        if not cursor.fetchone():
            cursor.execute("""
                INSERT INTO users (name, email, mobile, password, role, course_type)
                VALUES (%s, %s, %s, %s, 'admin', 'Admin')
            """, ("Admin", "admin@techeasy.com", "9876543210", generate_password_hash("admin123")))

        db.commit()
        cursor.close()
    else:
        cursor = db.cursor()

        # Users Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            mobile TEXT NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'student',
            course_type TEXT DEFAULT 'Degree',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # Safe migration: ensure course_type column exists
        cursor.execute("PRAGMA table_info(users)")
        user_cols = [row[1] for row in cursor.fetchall()]
        if 'course_type' not in user_cols:
            cursor.execute("ALTER TABLE users ADD COLUMN course_type TEXT DEFAULT 'Degree'")

        # Subjects Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_type TEXT NOT NULL,
            semester TEXT NOT NULL,
            subject_name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # Chapters Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS chapters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_id INTEGER NOT NULL,
            chapter_name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE
        );
        """)

        # Topics Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS topics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chapter_id INTEGER NOT NULL,
            topic_name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (chapter_id) REFERENCES chapters(id) ON DELETE CASCADE
        );
        """)

        # Questions Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_id INTEGER NOT NULL,
            chapter_id INTEGER NOT NULL,
            question TEXT NOT NULL,
            question_image TEXT DEFAULT '',
            option_a TEXT NOT NULL,
            option_a_image TEXT DEFAULT '',
            option_b TEXT NOT NULL,
            option_b_image TEXT DEFAULT '',
            option_c TEXT NOT NULL,
            option_c_image TEXT DEFAULT '',
            option_d TEXT NOT NULL,
            option_d_image TEXT DEFAULT '',
            correct_answer TEXT NOT NULL,
            explanation TEXT DEFAULT '',
            explanation_image TEXT DEFAULT '',
            difficulty TEXT DEFAULT 'Medium',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE,
            FOREIGN KEY (chapter_id) REFERENCES chapters(id) ON DELETE CASCADE
        );
        """)

        # Tests Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS tests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            test_name TEXT NOT NULL,
            course_type TEXT NOT NULL,
            subject_id INTEGER NOT NULL,
            number_of_questions INTEGER DEFAULT 0,
            time_limit INTEGER NOT NULL DEFAULT 30,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE
        );
        """)

        # Test Questions Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS test_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            test_id INTEGER NOT NULL,
            question_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (test_id) REFERENCES tests(id) ON DELETE CASCADE,
            FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE,
            UNIQUE(test_id, question_id)
        );
        """)

        # Mock Test Attempts Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            test_id INTEGER NOT NULL,
            score INTEGER NOT NULL DEFAULT 0,
            total_questions INTEGER NOT NULL DEFAULT 0,
            percentage REAL NOT NULL DEFAULT 0.0,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (test_id) REFERENCES tests(id) ON DELETE CASCADE
        );
        """)

        # Attempt Answers Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS attempt_answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            attempt_id INTEGER NOT NULL,
            question_id INTEGER NOT NULL,
            selected_answer TEXT DEFAULT '',
            is_correct INTEGER DEFAULT 0,
            FOREIGN KEY (attempt_id) REFERENCES attempts(id) ON DELETE CASCADE,
            FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE
        );
        """)

        # Practice Test Results Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS test_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            subject_id INTEGER NOT NULL,
            chapter_id INTEGER,
            total_questions INTEGER NOT NULL DEFAULT 0,
            correct_answers INTEGER NOT NULL DEFAULT 0,
            wrong_answers INTEGER NOT NULL DEFAULT 0,
            score INTEGER NOT NULL DEFAULT 0,
            percentage REAL NOT NULL DEFAULT 0.0,
            test_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE,
            FOREIGN KEY (chapter_id) REFERENCES chapters(id) ON DELETE SET NULL
        );
        """)

        # Video Lectures Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS video_lectures (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_type TEXT NOT NULL,
            youtube_link TEXT NOT NULL,
            description TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # Ensure default admin account exists
        from werkzeug.security import generate_password_hash
        cursor.execute("SELECT id FROM users WHERE email = ?", ("admin@techeasy.com",))
        if not cursor.fetchone():
            cursor.execute("""
                INSERT INTO users (name, email, mobile, password, role, course_type)
                VALUES (?, ?, ?, ?, 'admin', 'Admin')
            """, ("Admin", "admin@techeasy.com", "9876543210", generate_password_hash("admin123")))

        db.commit()
        cursor.close()

def extract_youtube_id(url):
    """Extract YouTube video ID from various YouTube URL formats."""
    if not url:
        return ""
    patterns = [
        r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/watch\?v=([a-zA-Z0-9_-]{11})',
        r'(?:https?:\/\/)?(?:www\.)?youtu\.be\/([a-zA-Z0-9_-]{11})',
        r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/embed\/([a-zA-Z0-9_-]{11})',
        r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/shorts\/([a-zA-Z0-9_-]{11})'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return ""

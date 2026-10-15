"""
Data Migration Utility: SQLite -> Cloud MySQL
Copies all existing subjects, chapters, questions, mock tests, users, and exam records
from local engineering_maths.db to your online MySQL database.
"""

import os
import sys
import sqlite3
import pymysql
from config import Config

TABLES = [
    'users',
    'subjects',
    'chapters',
    'topics',
    'questions',
    'tests',
    'test_questions',
    'attempts',
    'attempt_answers',
    'test_results',
    'video_lectures'
]

def migrate():
    print("=" * 60)
    print(" TechEasy Tutorials: SQLite -> Cloud MySQL Migration ")
    print("=" * 60)

    if not os.path.exists(Config.SQLITE_PATH):
        print(f"[ERROR] Local SQLite database not found at: {Config.SQLITE_PATH}")
        sys.exit(1)

    print(f"[*] Source SQLite: {Config.SQLITE_PATH}")
    print(f"[*] Target MySQL:  {Config.MYSQL_USER}@{Config.MYSQL_HOST}:{Config.MYSQL_PORT}/{Config.MYSQL_DB}")
    print(f"[*] SSL Enabled:   {Config.MYSQL_SSL}")
    print("-" * 60)

    # 1. Connect to MySQL
    try:
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

        mysql_conn = pymysql.connect(**kwargs)
        print("[OK] Connected to Cloud MySQL successfully!")
    except Exception as e:
        print(f"[ERROR] Failed to connect to MySQL: {e}")
        print("\nPlease check your .env configuration:")
        print("  DB_TYPE=mysql")
        print("  MYSQL_HOST=<your-cloud-host>")
        print("  MYSQL_PORT=<port, e.g. 3306 or 4000>")
        print("  MYSQL_USER=<user>")
        print("  MYSQL_PASSWORD=<password>")
        print("  MYSQL_DB=<database-name>")
        sys.exit(1)

    # 2. Temporarily switch Config.DATABASE_TYPE to 'mysql' and initialize tables
    original_type = Config.DATABASE_TYPE
    Config.DATABASE_TYPE = 'mysql'
    from database import init_db
    try:
        init_db()
        print("[OK] MySQL database tables created / verified.")
    except Exception as e:
        print(f"[ERROR] Error initializing MySQL tables: {e}")
        sys.exit(1)
    finally:
        Config.DATABASE_TYPE = original_type

    # 3. Connect to SQLite
    sqlite_conn = sqlite3.connect(Config.SQLITE_PATH)
    sqlite_conn.row_factory = sqlite3.Row

    # Disable foreign key checks during migration to allow arbitrary order
    with mysql_conn.cursor() as cur:
        cur.execute("SET FOREIGN_KEY_CHECKS = 0;")
        mysql_conn.commit()

    total_rows = 0
    for table in TABLES:
        try:
            s_cur = sqlite_conn.execute(f"SELECT * FROM {table}")
            rows = s_cur.fetchall()
            if not rows:
                print(f"[~] {table:18}: 0 rows (empty)")
                continue

            columns = list(rows[0].keys())
            placeholders = ', '.join(['%s'] * len(columns))
            cols_str = ', '.join([f"`{c}`" for c in columns])

            insert_sql = f"REPLACE INTO `{table}` ({cols_str}) VALUES ({placeholders})"

            with mysql_conn.cursor() as cur:
                for r in rows:
                    values = [r[c] for c in columns]
                    cur.execute(insert_sql, values)
                mysql_conn.commit()

            print(f"[+] {table:18}: {len(rows):4d} rows migrated")
            total_rows += len(rows)
        except Exception as e:
            print(f"[-] {table:18}: Warning/Error migrating table: {e}")

    # Re-enable foreign key checks
    with mysql_conn.cursor() as cur:
        cur.execute("SET FOREIGN_KEY_CHECKS = 1;")
        mysql_conn.commit()

    mysql_conn.close()
    sqlite_conn.close()

    print("-" * 60)
    print(f"[SUCCESS] Migration completed! Total {total_rows} records migrated to Cloud MySQL.")
    print("=" * 60)

if __name__ == '__main__':
    migrate()

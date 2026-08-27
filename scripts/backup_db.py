"""
Automated Database Backup Utility Script
Creates timestamped backups of SQLite database db/bot_history.db in db/backups/
"""

import os
import shutil
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "db", "bot_history.db")
BACKUP_DIR = os.path.join(BASE_DIR, "db", "backups")


def backup_database() -> str:
    """Creates a timestamped snapshot copy of bot_history.db."""
    if not os.path.exists(DB_PATH):
        logger.warning(f"Database file not found at {DB_PATH}. Creating empty database first.")
        from database import DatabaseService
        DatabaseService.init_db()

    os.makedirs(BACKUP_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"bot_history_backup_{timestamp}.db"
    backup_path = os.path.join(BACKUP_DIR, backup_filename)

    shutil.copy2(DB_PATH, backup_path)
    logger.info(f"✅ Database backup created successfully: {backup_path}")
    return backup_path


if __name__ == "__main__":
    path = backup_database()
    print(f"Database backup created at: {path}")

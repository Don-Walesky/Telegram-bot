"""
SQLite Database Service Module for Persistent Bet Slips & User History
Stores generated custom bet slips, code conversions, and user preferences.
"""

import os
import sqlite3
import logging
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

DB_DIR = os.path.join(os.path.dirname(__file__), "db")
DB_PATH = os.path.join(DB_DIR, "bot_history.db")


class DatabaseService:
    @classmethod
    def _get_connection(cls) -> sqlite3.Connection:
        os.makedirs(DB_DIR, exist_ok=True)
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

    @classmethod
    def init_db(cls) -> None:
        """Initialize database schema tables if not present."""
        with cls._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS generated_slips (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    match_date TEXT,
                    sport TEXT,
                    game_count INTEGER,
                    target_odds REAL,
                    actual_odds REAL,
                    min_probability REAL,
                    booking_code TEXT,
                    summary_text TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS code_conversions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    source_code TEXT,
                    source_bookmaker TEXT,
                    sportybet_code TEXT,
                    provider_used TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS user_preferences (
                    user_id INTEGER PRIMARY KEY,
                    target_date TEXT DEFAULT 'Today',
                    target_sport TEXT DEFAULT 'All',
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.commit()
            logger.info("✅ Database schema initialized successfully.")

    @classmethod
    def save_slip(
        cls,
        user_id: int,
        match_date: str,
        sport: str,
        game_count: int,
        target_odds: float,
        actual_odds: float,
        min_probability: float,
        booking_code: str,
        summary_text: str,
    ) -> int:
        with cls._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO generated_slips (
                    user_id, match_date, sport, game_count, target_odds,
                    actual_odds, min_probability, booking_code, summary_text
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    match_date,
                    sport,
                    game_count,
                    target_odds,
                    actual_odds,
                    min_probability,
                    booking_code,
                    summary_text,
                ),
            )
            conn.commit()
            return cursor.lastrowid

    @classmethod
    def save_conversion(
        cls,
        user_id: int,
        source_code: str,
        source_bookmaker: str,
        sportybet_code: str,
        provider_used: str,
    ) -> int:
        with cls._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO code_conversions (
                    user_id, source_code, source_bookmaker, sportybet_code, provider_used
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (user_id, source_code, source_bookmaker, sportybet_code, provider_used),
            )
            conn.commit()
            return cursor.lastrowid

    @classmethod
    def get_user_history(cls, user_id: int, limit: int = 5) -> List[Dict]:
        with cls._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM generated_slips
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (user_id, limit),
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    @classmethod
    def get_admin_stats(cls) -> Dict:
        with cls._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM generated_slips")
            total_slips = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM code_conversions")
            total_conversions = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(DISTINCT user_id) FROM generated_slips")
            unique_users = cursor.fetchone()[0]

            db_size_kb = round(os.path.getsize(DB_PATH) / 1024.0, 2) if os.path.exists(DB_PATH) else 0.0

            return {
                "total_slips": total_slips,
                "total_conversions": total_conversions,
                "unique_users": unique_users,
                "db_size_kb": db_size_kb,
            }


if __name__ == "__main__":
    DatabaseService.init_db()
    print("Database test init complete!")

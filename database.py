"""
SQLite Database Service Module for Persistent Bet Slips & User History
Stores generated custom bet slips, code conversions, and user preferences.
"""

import os
import sqlite3
import logging
from datetime import datetime
from typing import Dict, List, Optional
from config import config
from exceptions import DatabaseError

logger = logging.getLogger(__name__)

DB_DIR = config.app.db_dir
DB_PATH = config.app.db_path


class DatabaseService:
    _initialized = False

    @classmethod
    def _get_connection(cls) -> sqlite3.Connection:
        os.makedirs(DB_DIR, exist_ok=True)
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        if not cls._initialized:
            cls._ensure_tables(conn)
            cls._initialized = True
        return conn

    @classmethod
    def _ensure_tables(cls, conn: sqlite3.Connection) -> None:
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
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS tipster_market_learnings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                market_name TEXT UNIQUE,
                sport TEXT DEFAULT 'Football',
                occurrence_count INTEGER DEFAULT 1,
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS match_settlements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT UNIQUE,
                home_team TEXT,
                away_team TEXT,
                home_score INTEGER,
                away_score INTEGER,
                status TEXT DEFAULT 'FT',
                settled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()

    @classmethod
    def init_db(cls) -> None:
        """Initialize database schema tables if not present."""
        with cls._get_connection() as conn:
            cls._ensure_tables(conn)
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

    @classmethod
    def record_tipster_market(cls, market_name: str, sport: str = "Football") -> None:
        with cls._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO tipster_market_learnings (market_name, sport, occurrence_count, last_seen)
                VALUES (?, ?, 1, CURRENT_TIMESTAMP)
                ON CONFLICT(market_name) DO UPDATE SET
                    occurrence_count = occurrence_count + 1,
                    last_seen = CURRENT_TIMESTAMP
                """,
                (market_name, sport),
            )
    @classmethod
    def get_top_tipster_markets(cls, limit: int = 5) -> List[Dict]:
        with cls._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM tipster_market_learnings
                ORDER BY occurrence_count DESC, last_seen DESC
                LIMIT ?
                """,
                (limit,),
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    @classmethod
    def record_match_settlement(
        cls,
        event_id: str,
        home_team: str,
        away_team: str,
        home_score: int,
        away_score: int,
        status: str = "FT",
    ) -> int:
        with cls._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO match_settlements (event_id, home_team, away_team, home_score, away_score, status, settled_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(event_id) DO UPDATE SET
                    home_score = excluded.home_score,
                    away_score = excluded.away_score,
                    status = excluded.status,
                    settled_at = CURRENT_TIMESTAMP
                """,
                (event_id, home_team, away_team, home_score, away_score, status),
            )
            conn.commit()
            return cursor.lastrowid

    @classmethod
    def get_settled_match(cls, event_id: str) -> Optional[Dict]:
        with cls._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM match_settlements WHERE event_id = ?", (event_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    @classmethod
    def get_recent_settlements(cls, limit: int = 50) -> List[Dict]:
        with cls._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM match_settlements ORDER BY settled_at DESC LIMIT ?",
                (limit,),
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]


if __name__ == "__main__":
    DatabaseService.init_db()
    print("Database test init complete!")

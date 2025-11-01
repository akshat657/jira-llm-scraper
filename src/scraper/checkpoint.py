#!/usr/bin/env python3
"""
Checkpoint manager for fault-tolerant scraping
Uses SQLite to track progress and resume on failures
"""
import sqlite3
from datetime import datetime
from typing import Optional, Dict
from pathlib import Path


class CheckpointManager:
    """Manage scraping progress with SQLite"""
    
    def __init__(self, db_path: str):
        """
        Initialize checkpoint manager
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Create database tables if they don't exist"""
        with sqlite3.connect(self.db_path) as conn:
            # Checkpoints table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS checkpoints (
                    project TEXT PRIMARY KEY,
                    last_issue_key TEXT,
                    last_index INTEGER,
                    total_scraped INTEGER,
                    last_updated TIMESTAMP,
                    status TEXT
                )
            """)
            
            # Errors table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS errors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project TEXT,
                    issue_key TEXT,
                    error_message TEXT,
                    timestamp TIMESTAMP
                )
            """)
            
            # Statistics table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS statistics (
                    project TEXT PRIMARY KEY,
                    total_issues INTEGER,
                    total_comments INTEGER,
                    start_time TIMESTAMP,
                    end_time TIMESTAMP,
                    duration_seconds REAL
                )
            """)
            
            conn.commit()
    
    def get_checkpoint(self, project: str) -> Optional[Dict]:
        """
        Get last checkpoint for a project
        
        Args:
            project: Project key (e.g., 'KAFKA')
            
        Returns:
            Dictionary with checkpoint data or None
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM checkpoints WHERE project = ?",
                (project,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def save_checkpoint(
        self,
        project: str,
        last_issue_key: str,
        last_index: int,
        total_scraped: int
    ):
        """
        Save progress checkpoint
        
        Args:
            project: Project key
            last_issue_key: Last successfully scraped issue
            last_index: API pagination index
            total_scraped: Total issues scraped so far
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO checkpoints 
                (project, last_issue_key, last_index, total_scraped, last_updated, status)
                VALUES (?, ?, ?, ?, ?, 'in_progress')
            """, (project, last_issue_key, last_index, total_scraped, datetime.now()))
            conn.commit()
    
    def mark_complete(self, project: str):
        """Mark project scraping as completed"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE checkpoints SET status = 'completed', last_updated = ? WHERE project = ?",
                (datetime.now(), project)
            )
            conn.commit()
    
    def log_error(self, project: str, issue_key: str, error: str):
        """
        Log an error for later review
        
        Args:
            project: Project key
            issue_key: Issue that failed
            error: Error message
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO errors (project, issue_key, error_message, timestamp)
                VALUES (?, ?, ?, ?)
            """, (project, issue_key, error, datetime.now()))
            conn.commit()
    
    def save_statistics(
        self,
        project: str,
        total_issues: int,
        total_comments: int,
        start_time: datetime,
        end_time: datetime
    ):
        """Save scraping statistics"""
        duration = (end_time - start_time).total_seconds()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO statistics
                (project, total_issues, total_comments, start_time, end_time, duration_seconds)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (project, total_issues, total_comments, start_time, end_time, duration))
            conn.commit()
    
    def get_statistics(self, project: str) -> Optional[Dict]:
        """Get statistics for a project"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM statistics WHERE project = ?",
                (project,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def reset_project(self, project: str):
        """Reset checkpoint for a project (start from scratch)"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM checkpoints WHERE project = ?", (project,))
            conn.execute("DELETE FROM errors WHERE project = ?", (project,))
            conn.execute("DELETE FROM statistics WHERE project = ?", (project,))
            conn.commit()
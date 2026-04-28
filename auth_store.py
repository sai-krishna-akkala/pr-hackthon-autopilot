from __future__ import annotations

import hashlib
import hmac
import os
import re
import sqlite3
from pathlib import Path
from typing import Any


EMAIL_PATTERN = re.compile(r"^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$", re.IGNORECASE)
DB_PATH = Path(__file__).resolve().parent / "data" / "app.db"
PBKDF2_ITERATIONS = 200_000


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    with _connect() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS review_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_email TEXT NOT NULL,
                repository TEXT,
                pr_number TEXT,
                head_branch TEXT,
                base_branch TEXT,
                status TEXT NOT NULL,
                return_code INTEGER,
                risk_score TEXT,
                risk_level TEXT,
                decision TEXT,
                total_issues TEXT,
                stdout_text TEXT,
                stderr_text TEXT,
                combined_logs TEXT,
                error_message TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.commit()


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _validate_email(email: str) -> bool:
    return bool(EMAIL_PATTERN.fullmatch(_normalize_email(email)))


def _validate_password(password: str) -> str | None:
    if len(password) < 8:
        return "Password must be at least 8 characters long."
    if not re.search(r"[A-Za-z]", password):
        return "Password must include at least one letter."
    if not re.search(r"\d", password):
        return "Password must include at least one number."
    return None


def _hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return f"{PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


def _verify_password(password: str, stored_hash: str) -> bool:
    try:
        iteration_text, salt_hex, digest_hex = stored_hash.split("$", maxsplit=2)
        iterations = int(iteration_text)
        salt = bytes.fromhex(salt_hex)
        expected_digest = bytes.fromhex(digest_hex)
    except (TypeError, ValueError):
        return False

    current_digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(current_digest, expected_digest)


def create_user(email: str, password: str) -> tuple[bool, str]:
    normalized_email = _normalize_email(email)
    if not _validate_email(normalized_email):
        return False, "Enter a valid email address."

    password_error = _validate_password(password)
    if password_error:
        return False, password_error

    password_hash = _hash_password(password)
    try:
        with _connect() as connection:
            connection.execute(
                "INSERT INTO users (email, password_hash) VALUES (?, ?)",
                (normalized_email, password_hash),
            )
            connection.commit()
    except sqlite3.IntegrityError:
        return False, "An account with this email already exists."

    return True, "Account created successfully. You can log in now."


def authenticate_user(email: str, password: str) -> dict[str, str] | None:
    normalized_email = _normalize_email(email)
    if not normalized_email or not password:
        return None

    with _connect() as connection:
        row = connection.execute(
            "SELECT id, email, password_hash FROM users WHERE email = ?",
            (normalized_email,),
        ).fetchone()

    if not row or not _verify_password(password, row["password_hash"]):
        return None

    return {"id": str(row["id"]), "email": row["email"]}


def save_review_run(
    *,
    user_email: str,
    repository: str,
    pr_number: str,
    head_branch: str,
    base_branch: str,
    status: str,
    return_code: int | None,
    risk_score: str,
    risk_level: str,
    decision: str,
    total_issues: str,
    stdout_text: str,
    stderr_text: str,
    combined_logs: str,
    error_message: str,
) -> None:
    with _connect() as connection:
        connection.execute(
            """
            INSERT INTO review_runs (
                user_email,
                repository,
                pr_number,
                head_branch,
                base_branch,
                status,
                return_code,
                risk_score,
                risk_level,
                decision,
                total_issues,
                stdout_text,
                stderr_text,
                combined_logs,
                error_message
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_email.strip().lower(),
                repository,
                pr_number,
                head_branch,
                base_branch,
                status,
                return_code,
                risk_score,
                risk_level,
                decision,
                total_issues,
                stdout_text,
                stderr_text,
                combined_logs,
                error_message,
            ),
        )
        connection.commit()


def list_review_runs(user_email: str, limit: int = 20) -> list[dict[str, Any]]:
    normalized_email = user_email.strip().lower()
    with _connect() as connection:
        rows = connection.execute(
            """
            SELECT
                id,
                user_email,
                repository,
                pr_number,
                head_branch,
                base_branch,
                status,
                return_code,
                risk_score,
                risk_level,
                decision,
                total_issues,
                stdout_text,
                stderr_text,
                combined_logs,
                error_message,
                created_at
            FROM review_runs
            WHERE user_email = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (normalized_email, limit),
        ).fetchall()

    return [dict(row) for row in rows]
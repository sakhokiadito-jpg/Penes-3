import secrets
import sqlite3
import time

from config import DATABASE_PATH, DEFAULT_CREDITS


def get_connection():
    connection = sqlite3.connect(
        DATABASE_PATH
    )
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    with get_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                tg_id INTEGER PRIMARY KEY,
                username TEXT,
                credits INTEGER NOT NULL DEFAULT 0,
                is_owner INTEGER NOT NULL DEFAULT 0,
                is_admin INTEGER NOT NULL DEFAULT 0,
                free_access INTEGER NOT NULL DEFAULT 0,
                created_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS reports (
                token TEXT PRIMARY KEY,
                tg_id INTEGER NOT NULL,
                payload TEXT NOT NULL,
                expires_at INTEGER NOT NULL,
                created_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tg_id INTEGER NOT NULL,
                payload TEXT NOT NULL,
                stars INTEGER NOT NULL,
                charge_id TEXT,
                created_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS group_settings (
                chat_id INTEGER PRIMARY KEY,
                enabled INTEGER NOT NULL DEFAULT 0,
                created_at INTEGER NOT NULL
            );
            """
        )


def ensure_user(
    tg_id: int,
    username: str | None = None,
    is_owner: bool = False,
    is_admin: bool = False,
    free_access: bool = False,
):
    with get_connection() as connection:
        existing = connection.execute(
            "SELECT tg_id FROM users WHERE tg_id = ?",
            (tg_id,),
        ).fetchone()

        if existing is None:
            connection.execute(
                """
                INSERT INTO users
                (
                    tg_id,
                    username,
                    credits,
                    is_owner,
                    is_admin,
                    free_access,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    tg_id,
                    username,
                    DEFAULT_CREDITS,
                    int(is_owner),
                    int(is_admin),
                    int(free_access),
                    int(time.time()),
                ),
            )
        else:
            connection.execute(
                """
                UPDATE users
                SET username = ?,
                    is_owner = MAX(is_owner, ?),
                    is_admin = MAX(is_admin, ?),
                    free_access = MAX(free_access, ?)
                WHERE tg_id = ?
                """,
                (
                    username,
                    int(is_owner),
                    int(is_admin),
                    int(free_access),
                    tg_id,
                ),
            )


def get_user(tg_id: int):
    with get_connection() as connection:
        return connection.execute(
            """
            SELECT *
            FROM users
            WHERE tg_id = ?
            """,
            (tg_id,),
        ).fetchone()


def has_unlimited_access(
    tg_id: int,
    group_chat: bool = False,
) -> bool:
    user = get_user(tg_id)

    if not user:
        return group_chat

    return bool(
        user["is_owner"]
        or user["is_admin"]
        or user["free_access"]
        or group_chat
    )


def charge_search(
    tg_id: int,
    group_chat: bool = False,
) -> bool:
    if has_unlimited_access(
        tg_id,
        group_chat=group_chat,
    ):
        return True

    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT credits
            FROM users
            WHERE tg_id = ?
            """,
            (tg_id,),
        ).fetchone()

        if not row:
            return False

        if row["credits"] <= 0:
            return False

        connection.execute(
            """
            UPDATE users
            SET credits = credits - 1
            WHERE tg_id = ?
            """,
            (tg_id,),
        )

        return True


def grant_credits(
    tg_id: int,
    amount: int,
):
    with get_connection() as connection:
        connection.execute(
            """
            UPDATE users
            SET credits = credits + ?
            WHERE tg_id = ?
            """,
            (amount, tg_id),
        )


def set_credits(
    tg_id: int,
    amount: int,
):
    with get_connection() as connection:
        connection.execute(
            """
            UPDATE users
            SET credits = ?
            WHERE tg_id = ?
            """,
            (amount, tg_id),
        )


def save_payment(
    tg_id: int,
    payload: str,
    stars: int,
    charge_id: str | None,
):
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO payments
            (
                tg_id,
                payload,
                stars,
                charge_id,
                created_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                tg_id,
                payload,
                stars,
                charge_id,
                int(time.time()),
            ),
        )


def create_report(
    tg_id: int,
    payload: str,
    ttl_seconds: int,
) -> str:
    token = secrets.token_urlsafe(24)

    now = int(time.time())
    expires_at = now + ttl_seconds

    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO reports
            (
                token,
                tg_id,
                payload,
                expires_at,
                created_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                token,
                tg_id,
                payload,
                expires_at,
                now,
            ),
        )

    return token


def get_report(token: str):
    with get_connection() as connection:
        return connection.execute(
            """
            SELECT *
            FROM reports
            WHERE token = ?
              AND expires_at >= ?
            """,
            (
                token,
                int(time.time()),
            ),
        ).fetchone()


def enable_group(chat_id: int):
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO group_settings
            (
                chat_id,
                enabled,
                created_at
            )
            VALUES (?, 1, ?)
            ON CONFLICT(chat_id)
            DO UPDATE SET enabled = 1
            """,
            (
                chat_id,
                int(time.time()),
            ),
        )


def group_enabled(chat_id: int) -> bool:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT enabled
            FROM group_settings
            WHERE chat_id = ?
            """,
            (chat_id,),
        ).fetchone()

    return bool(row and row["enabled"])

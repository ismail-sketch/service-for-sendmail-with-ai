import os
import sqlite3

import config


def _conn():
    c = sqlite3.connect(config.DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def init_db():
    d = os.path.dirname(config.DB_PATH)
    if d:
        os.makedirs(d, exist_ok=True)
    c = _conn()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            text TEXT NOT NULL,
            remind_at INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending'
        )
        """
    )
    c.execute("CREATE INDEX IF NOT EXISTS idx_status ON reminders(status)")
    c.commit()
    c.close()


def add_reminder(chat_id, text, remind_at):
    c = _conn()
    cur = c.execute(
        "INSERT INTO reminders (chat_id, text, remind_at, status) VALUES (?, ?, ?, 'pending')",
        (chat_id, text, remind_at),
    )
    c.commit()
    rid = cur.lastrowid
    c.close()
    return rid


def due_reminders(now):
    c = _conn()
    rows = c.execute(
        "SELECT id, chat_id, text, remind_at FROM reminders "
        "WHERE status = 'pending' AND remind_at <= ?",
        (now,),
    ).fetchall()
    c.close()
    return [dict(r) for r in rows]


def mark_done(rid):
    c = _conn()
    c.execute(
        "UPDATE reminders SET status = 'done' WHERE id = ? AND status = 'pending'", (rid,)
    )
    c.commit()
    c.close()


def mark_pending(rid):
    c = _conn()
    c.execute(
        "UPDATE reminders SET status = 'pending' WHERE id = ? AND status = 'done'", (rid,)
    )
    c.commit()
    c.close()


def list_pending(chat_id, now):
    c = _conn()
    rows = c.execute(
        "SELECT id, text, remind_at FROM reminders "
        "WHERE chat_id = ? AND status = 'pending' AND remind_at > ? ORDER BY remind_at",
        (chat_id, now),
    ).fetchall()
    c.close()
    return [dict(r) for r in rows]


def delete_reminder(rid, chat_id):
    c = _conn()
    cur = c.execute(
        "DELETE FROM reminders WHERE id = ? AND chat_id = ? AND status = 'pending'",
        (rid, chat_id),
    )
    c.commit()
    deleted = cur.rowcount > 0
    c.close()
    return deleted
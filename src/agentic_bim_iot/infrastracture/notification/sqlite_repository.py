import sqlite3
import time
from pathlib import Path
from threading import Lock

from agentic_bim_iot.application.interfaces.notification_repository import NotificationRepositoryError
from agentic_bim_iot.domain.notification import Notification, NotificationStatus


class SQLiteNotificationRepository:
    """The SQLite Notification repository implementation"""
    def __init__(self, database_path: str) -> None:
        self._database_path = database_path
        self._lock = Lock()
        path = Path(database_path)
        if path.parent != Path("."):
            path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def save(self, notification: Notification) -> None:
        try:
            with self._lock:
                with self._connect() as connection:
                    connection.execute(
                        """
                        INSERT INTO notifications (
                            notification_id,
                            notification_type,
                            status,
                            room_reference,
                            proposal_id,
                            created_at_ms,
                            payload
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (notification.notification_id, notification.notification_type.value, notification.status.value, notification.room_reference, notification.proposal_id, notification.created_at_ms, notification.model_dump_json()),
                    )
                    connection.commit()
        except sqlite3.IntegrityError as exc:
            raise NotificationRepositoryError(f"A notification already exists for proposal '{notification.proposal_id}'.") from exc
        except sqlite3.Error as exc:
            raise NotificationRepositoryError(f"Could not save notification: {exc}") from exc


    def get(self, notification_id: str) -> Notification | None:
        try:
            with self._lock:
                with self._connect() as connection:
                    row = connection.execute("SELECT payload FROM notifications WHERE notification_id = ?", (notification_id,)).fetchone()
        except sqlite3.Error as exc:
            raise NotificationRepositoryError(f"Could not retrieve notification: {exc}") from exc
        return Notification.model_validate_json(row[0]) if row else None



    def list_unread(self) -> list[Notification]:
        try:
            with self._lock:
                with self._connect() as connection:
                    rows = connection.execute(
                        """
                        SELECT payload
                        FROM notifications
                        WHERE status = ?
                        ORDER BY created_at_ms DESC
                        """,
                        (NotificationStatus.UNREAD.value,)
                    ).fetchall()
        except sqlite3.Error as exc:
            raise NotificationRepositoryError(f"Could not retrieve unread notifications: {exc}") from exc
        return [Notification.model_validate_json(row[0]) for row in rows]



    def mark_read(self, notification_id: str) -> None:
        notification = self.get(notification_id)
        if notification is None:
            raise NotificationRepositoryError(f"Notification '{notification_id}' does not exist.")
        if notification.status == NotificationStatus.RESOLVED:
            return
        updated = notification.model_copy(update={"status": NotificationStatus.READ, "read_at_ms": time.time_ns() // 1_000_000})
        self._update(updated)

    def resolve_by_proposal(self, proposal_id: str) -> None:
        current_time_ms = time.time_ns() // 1_000_000
        try:
            with self._lock:
                with self._connect() as connection:
                    rows = connection.execute(
                        """
                        SELECT notification_id, payload
                        FROM notifications
                        WHERE proposal_id = ?
                        AND status != ?
                        """,
                        (proposal_id, NotificationStatus.RESOLVED.value)
                    ).fetchall()
                    for notification_id, payload in rows:
                        notification = Notification.model_validate_json(payload)
                        resolved = notification.model_copy(update={"status": NotificationStatus.RESOLVED, "resolved_at_ms": current_time_ms})
                        connection.execute(
                            """
                            UPDATE notifications
                            SET status = ?, payload = ?
                            WHERE notification_id = ?
                            """,
                            (resolved.status.value, resolved.model_dump_json(), notification_id),
                        )
                    connection.commit()
        except sqlite3.Error as exc:
            raise NotificationRepositoryError(f"Could not resolve proposal notifications: {exc}") from exc


    def _update(self, notification: Notification) -> None:
        try:
            with self._lock:
                with self._connect() as connection:
                    cursor = connection.execute(
                        """
                        UPDATE notifications
                        SET status = ?, payload = ?
                        WHERE notification_id = ?
                        """,
                        (notification.status.value, notification.model_dump_json(), notification.notification_id)
                    )
                    if cursor.rowcount == 0:
                        raise NotificationRepositoryError(f"Notification '{notification.notification_id}' does not exist.")
                    connection.commit()
        except NotificationRepositoryError:
            raise
        except sqlite3.Error as exc:
            raise NotificationRepositoryError(f"Could not update notification: {exc}") from exc


    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path, timeout=5.0)
        connection.execute("PRAGMA busy_timeout=5000")
        return connection



    def _initialize(self) -> None:
        try:
            with self._connect() as connection:
                connection.execute("PRAGMA journal_mode=WAL")
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS notifications (
                        notification_id TEXT PRIMARY KEY,
                        notification_type TEXT NOT NULL,
                        status TEXT NOT NULL,
                        room_reference TEXT NOT NULL,
                        proposal_id TEXT,
                        created_at_ms INTEGER NOT NULL,
                        payload TEXT NOT NULL,
                        UNIQUE(proposal_id, notification_type)
                    )
                    """
                )
                connection.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_notifications_status_created
                    ON notifications(status, created_at_ms DESC)
                    """
                )
                connection.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_notifications_proposal
                    ON notifications(proposal_id)
                    """
                )
                connection.commit()
        except sqlite3.Error as exc:
            raise NotificationRepositoryError(f"Could not initialize notification repository: {exc}") from exc
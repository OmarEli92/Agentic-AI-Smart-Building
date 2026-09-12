import sqlite3
import time
from pathlib import Path
from threading import Lock

from agentic_bim_iot.application.interfaces.proposal_repository import ProposalRepositoryError
from agentic_bim_iot.domain.proposal import ActionProposal, ProposalSource, ProposalStatus


class SQLiteProposalRepository:
    """SQLite repository for persistent action proposals."""

    def __init__(self, database_path: str) -> None:
        self._database_path = database_path
        self._lock = Lock()
        path = Path(database_path)
        if path.parent != Path("."):
            path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()


    def save(self, proposal: ActionProposal) -> None:
        current_time_ms = time.time_ns() // 1_000_000
        try:
            with self._lock:
                with self._connect() as connection:
                    self._expire_pending_proposals_for_room(connection=connection, room_reference=proposal.room_reference, current_time_ms=current_time_ms)

                    if proposal.source == ProposalSource.PROACTIVE_MONITOR:
                        query = (
                            "SELECT proposal_id FROM action_proposals "
                            "WHERE status = ? AND expires_at_ms > ? AND LOWER(room_reference) = LOWER(?) "
                            "ORDER BY created_at_ms DESC LIMIT 1"
                        )
                        existing = connection.execute(
                            query,
                            (ProposalStatus.PENDING_APPROVAL.value, current_time_ms, proposal.room_reference.strip()),
                        ).fetchone()

                        if existing is not None:
                            raise ProposalRepositoryError(f"A pending proposal already exists for room '{proposal.room_reference}'.")
                    else:
                        self._supersede_pending_proposals_for_room(connection=connection, room_reference=proposal.room_reference)

                    insert_sql = (
                        "INSERT INTO action_proposals "
                        "(proposal_id, room_reference, status, created_at_ms, expires_at_ms, payload) "
                        "VALUES (?, ?, ?, ?, ?, ?)"
                    )
                    connection.execute(
                        insert_sql,
                        (proposal.proposal_id, proposal.room_reference, proposal.status.value, proposal.created_at_ms, proposal.expires_at_ms, proposal.model_dump_json()),
                    )
                    connection.commit()

        except ProposalRepositoryError:
            raise
        except sqlite3.Error as exc:
            raise ProposalRepositoryError(f"Could not save the action proposal: {exc}") from exc

    def get(self, proposal_id: str) -> ActionProposal | None:
        try:
            with self._lock:
                with self._connect() as connection:
                    row = connection.execute("SELECT payload FROM action_proposals WHERE proposal_id = ?", (proposal_id,)).fetchone()
        except sqlite3.Error as exc:
            raise ProposalRepositoryError(f"Could not retrieve the action proposal: {exc}") from exc

        return ActionProposal.model_validate_json(row[0]) if row else None

    def get_latest(self, room_reference: str) -> ActionProposal | None:
        room = room_reference.strip()
        if not room:
            raise ProposalRepositoryError("Room reference cannot be empty.")

        try:
            with self._lock:
                with self._connect() as connection:
                    query = "SELECT payload FROM action_proposals WHERE LOWER(room_reference) = LOWER(?) ORDER BY created_at_ms DESC LIMIT 1"
                    row = connection.execute(query, (room,)).fetchone()
        except sqlite3.Error as exc:
            raise ProposalRepositoryError(f"Could not retrieve the latest action proposal: {exc}") from exc

        return ActionProposal.model_validate_json(row[0]) if row else None

    def get_latest_pending(self, room_reference: str | None = None) -> ActionProposal | None:
        proposals = self.list_pending(room_reference=room_reference)
        return proposals[0] if proposals else None

    def list_pending(self, room_reference: str | None = None) -> list[ActionProposal]:
        current_time_ms = time.time_ns() // 1_000_000
        try:
            with self._lock:
                with self._connect() as connection:
                    if room_reference is None:
                        query = "SELECT payload FROM action_proposals WHERE status = ? AND expires_at_ms > ? ORDER BY created_at_ms DESC"
                        rows = connection.execute(query, (ProposalStatus.PENDING_APPROVAL.value, current_time_ms)).fetchall()
                    else:
                        query = "SELECT payload FROM action_proposals WHERE status = ? AND expires_at_ms > ? AND LOWER(room_reference) = LOWER(?) ORDER BY created_at_ms DESC"
                        rows = connection.execute(query, (ProposalStatus.PENDING_APPROVAL.value, current_time_ms, room_reference.strip())).fetchall()
        except sqlite3.Error as exc:
            raise ProposalRepositoryError(f"Could not retrieve pending action proposals: {exc}") from exc

        return [ActionProposal.model_validate_json(row[0]) for row in rows]

    def update(self, proposal: ActionProposal) -> None:
        try:
            with self._lock:
                with self._connect() as connection:
                    update_sql = (
                        "UPDATE action_proposals "
                        "SET room_reference = ?, status = ?, created_at_ms = ?, expires_at_ms = ?, payload = ? "
                        "WHERE proposal_id = ?"
                    )
                    cursor = connection.execute(
                        update_sql,
                        (proposal.room_reference, proposal.status.value, proposal.created_at_ms, proposal.expires_at_ms, proposal.model_dump_json(), proposal.proposal_id),
                    )
                    if cursor.rowcount == 0:
                        raise ProposalRepositoryError(f"Proposal '{proposal.proposal_id}' does not exist.")
                    connection.commit()

        except ProposalRepositoryError:
            raise
        except sqlite3.Error as exc:
            raise ProposalRepositoryError(f"Could not update the action proposal: {exc}") from exc

    def supersede(self, proposal: ActionProposal, replacement: ActionProposal) -> None:
        superseded_proposal = proposal.model_copy(update={"status": ProposalStatus.SUPERSEDED})
        try:
            with self._lock:
                with self._connect() as connection:
                    current_row = connection.execute("SELECT status FROM action_proposals WHERE proposal_id = ?", (proposal.proposal_id,)).fetchone()
                    if current_row is None:
                        raise ProposalRepositoryError(f"Proposal '{proposal.proposal_id}' does not exist.")
                    if current_row[0] != ProposalStatus.PENDING_APPROVAL.value:
                        raise ProposalRepositoryError(f"Proposal '{proposal.proposal_id}' is no longer pending approval.")

                    insert_sql = (
                        "INSERT INTO action_proposals "
                        "(proposal_id, room_reference, status, created_at_ms, expires_at_ms, payload) "
                        "VALUES (?, ?, ?, ?, ?, ?)"
                    )
                    connection.execute(
                        insert_sql,
                        (replacement.proposal_id, replacement.room_reference, replacement.status.value, replacement.created_at_ms, replacement.expires_at_ms, replacement.model_dump_json()),
                    )
                    connection.execute(
                        "UPDATE action_proposals SET status = ?, payload = ? WHERE proposal_id = ?",
                        (superseded_proposal.status.value, superseded_proposal.model_dump_json(), superseded_proposal.proposal_id),
                    )
                    connection.commit()

        except ProposalRepositoryError:
            raise
        except sqlite3.Error as exc:
            raise ProposalRepositoryError(f"Could not supersede the action proposal: {exc}") from exc

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path, timeout=5.0)
        connection.execute("PRAGMA busy_timeout=5000")
        return connection

    @staticmethod
    def _supersede_pending_proposals_for_room(connection: sqlite3.Connection, room_reference: str) -> None:
        query = "SELECT proposal_id, payload FROM action_proposals WHERE status = ? AND LOWER(room_reference) = LOWER(?) ORDER BY created_at_ms DESC"
        rows = connection.execute(query, (ProposalStatus.PENDING_APPROVAL.value, room_reference.strip())).fetchall()

        for proposal_id, payload in rows:
            proposal = ActionProposal.model_validate_json(payload)
            superseded = proposal.model_copy(update={"status": ProposalStatus.SUPERSEDED})
            connection.execute(
                "UPDATE action_proposals SET status = ?, payload = ? WHERE proposal_id = ?",
                (ProposalStatus.SUPERSEDED.value, superseded.model_dump_json(), proposal_id),
            )

    @staticmethod
    def _expire_pending_proposals_for_room(connection: sqlite3.Connection, room_reference: str, current_time_ms: int) -> None:
        query = "SELECT proposal_id, payload FROM action_proposals WHERE status = ? AND expires_at_ms <= ? AND LOWER(room_reference) = LOWER(?)"
        rows = connection.execute(query, (ProposalStatus.PENDING_APPROVAL.value, current_time_ms, room_reference.strip())).fetchall()

        for proposal_id, payload in rows:
            proposal = ActionProposal.model_validate_json(payload)
            expired = proposal.model_copy(update={"status": ProposalStatus.EXPIRED})
            connection.execute(
                "UPDATE action_proposals SET status = ?, payload = ? WHERE proposal_id = ?",
                (ProposalStatus.EXPIRED.value, expired.model_dump_json(), proposal_id),
            )

    def _initialize(self) -> None:
        try:
            with self._connect() as connection:
                connection.execute("PRAGMA journal_mode=WAL")
                connection.execute("CREATE TABLE IF NOT EXISTS action_proposals (proposal_id TEXT PRIMARY KEY, room_reference TEXT NOT NULL, status TEXT NOT NULL, created_at_ms INTEGER NOT NULL, expires_at_ms INTEGER NOT NULL, payload TEXT NOT NULL)")
                connection.execute("CREATE INDEX IF NOT EXISTS idx_action_proposals_status_created ON action_proposals(status, created_at_ms DESC)")
                connection.execute("CREATE INDEX IF NOT EXISTS idx_action_proposals_room_status ON action_proposals(room_reference, status)")
                connection.commit()
        except sqlite3.Error as exc:
            raise ProposalRepositoryError(f"Could not initialize the proposal repository: {exc}") from exc
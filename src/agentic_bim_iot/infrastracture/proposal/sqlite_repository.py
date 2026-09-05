import sqlite3
import time
from pathlib import Path
from threading import Lock

from agentic_bim_iot.application.interfaces.proposal_repository import ProposalRepositoryError
from agentic_bim_iot.domain.proposal import ActionProposal, ProposalStatus


class SQLiteProposalRepository:
    def __init__(self, database_path: str) -> None:
        self._database_path = database_path
        self._lock = Lock()

        path = Path(database_path)
        if path.parent != Path("."):
            path.parent.mkdir(parents=True, exist_ok=True)

        self._initialize()

    def save(self, proposal: ActionProposal) -> None:
        try:
            with self._lock:
                with sqlite3.connect(self._database_path) as connection:
                    self._supersede_pending_proposals_for_room(
                        connection=connection,
                        room_reference=proposal.room_reference,
                    )
                    connection.execute(
                        """
                        INSERT INTO action_proposals (
                            proposal_id, room_reference, status,
                            created_at_ms, expires_at_ms, payload
                        ) VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            proposal.proposal_id,
                            proposal.room_reference,
                            proposal.status.value,
                            proposal.created_at_ms,
                            proposal.expires_at_ms,
                            proposal.model_dump_json(),
                        ),
                    )
                    connection.commit()
        except sqlite3.Error as exc:
            raise ProposalRepositoryError(f"Could not save the action proposal: {exc}") from exc

    def get(self, proposal_id: str) -> ActionProposal | None:
        try:
            with self._lock:
                with sqlite3.connect(self._database_path) as connection:
                    row = connection.execute(
                        "SELECT payload FROM action_proposals WHERE proposal_id = ?",
                        (proposal_id,),
                    ).fetchone()
        except sqlite3.Error as exc:
            raise ProposalRepositoryError(f"Could not retrieve the action proposal: {exc}") from exc

        return ActionProposal.model_validate_json(row[0]) if row else None

    def get_latest_pending(self, room_reference: str | None = None) -> ActionProposal | None:
        proposals = self.list_pending(room_reference=room_reference)
        return proposals[0] if proposals else None

    def list_pending(self, room_reference: str | None = None) -> list[ActionProposal]:
        current_time_ms = time.time_ns() // 1_000_000

        try:
            with self._lock:
                with sqlite3.connect(self._database_path) as connection:
                    if room_reference is None:
                        rows = connection.execute(
                            """
                            SELECT payload FROM action_proposals
                            WHERE status = ? AND expires_at_ms > ?
                            ORDER BY created_at_ms DESC
                            """,
                            (ProposalStatus.PENDING_APPROVAL.value, current_time_ms),
                        ).fetchall()
                    else:
                        rows = connection.execute(
                            """
                            SELECT payload FROM action_proposals
                            WHERE status = ? AND expires_at_ms > ?
                            AND LOWER(room_reference) = LOWER(?)
                            ORDER BY created_at_ms DESC
                            """,
                            (
                                ProposalStatus.PENDING_APPROVAL.value,
                                current_time_ms,
                                room_reference.strip(),
                            ),
                        ).fetchall()
        except sqlite3.Error as exc:
            raise ProposalRepositoryError(f"Could not retrieve pending action proposals: {exc}") from exc

        return [ActionProposal.model_validate_json(row[0]) for row in rows]

    def update(self, proposal: ActionProposal) -> None:
        try:
            with self._lock:
                with sqlite3.connect(self._database_path) as connection:
                    cursor = connection.execute(
                        """
                        UPDATE action_proposals
                        SET room_reference = ?, status = ?, created_at_ms = ?,
                            expires_at_ms = ?, payload = ?
                        WHERE proposal_id = ?
                        """,
                        (
                            proposal.room_reference,
                            proposal.status.value,
                            proposal.created_at_ms,
                            proposal.expires_at_ms,
                            proposal.model_dump_json(),
                            proposal.proposal_id,
                        ),
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
                with sqlite3.connect(self._database_path) as connection:
                    current_row = connection.execute(
                        "SELECT status FROM action_proposals WHERE proposal_id = ?",
                        (proposal.proposal_id,),
                    ).fetchone()

                    if current_row is None:
                        raise ProposalRepositoryError(f"Proposal '{proposal.proposal_id}' does not exist.")
                    if current_row[0] != ProposalStatus.PENDING_APPROVAL.value:
                        raise ProposalRepositoryError(f"Proposal '{proposal.proposal_id}' is no longer pending approval.")

                    connection.execute(
                        """
                        INSERT INTO action_proposals (
                            proposal_id, room_reference, status,
                            created_at_ms, expires_at_ms, payload
                        ) VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            replacement.proposal_id,
                            replacement.room_reference,
                            replacement.status.value,
                            replacement.created_at_ms,
                            replacement.expires_at_ms,
                            replacement.model_dump_json(),
                        ),
                    )

                    connection.execute(
                        "UPDATE action_proposals SET status = ?, payload = ? WHERE proposal_id = ?",
                        (
                            superseded_proposal.status.value,
                            superseded_proposal.model_dump_json(),
                            superseded_proposal.proposal_id,
                        ),
                    )
                    connection.commit()
        except ProposalRepositoryError:
            raise
        except sqlite3.Error as exc:
            raise ProposalRepositoryError(f"Could not supersede the action proposal: {exc}") from exc

    @staticmethod
    def _supersede_pending_proposals_for_room(connection: sqlite3.Connection, room_reference: str) -> None:
        rows = connection.execute(
            """
            SELECT proposal_id, payload FROM action_proposals
            WHERE status = ? AND LOWER(room_reference) = LOWER(?)
            ORDER BY created_at_ms DESC
            """,
            (ProposalStatus.PENDING_APPROVAL.value, room_reference.strip()),
        ).fetchall()

        for proposal_id, payload in rows:
            proposal = ActionProposal.model_validate_json(payload)
            superseded = proposal.model_copy(update={"status": ProposalStatus.SUPERSEDED})

            connection.execute(
                "UPDATE action_proposals SET status = ?, payload = ? WHERE proposal_id = ?",
                (ProposalStatus.SUPERSEDED.value, superseded.model_dump_json(), proposal_id),
            )

    def _initialize(self) -> None:
        try:
            with sqlite3.connect(self._database_path) as connection:
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS action_proposals (
                        proposal_id TEXT PRIMARY KEY,
                        room_reference TEXT NOT NULL,
                        status TEXT NOT NULL,
                        created_at_ms INTEGER NOT NULL,
                        expires_at_ms INTEGER NOT NULL,
                        payload TEXT NOT NULL
                    )
                    """
                )
                connection.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_action_proposals_status_created
                    ON action_proposals(status, created_at_ms DESC)
                    """
                )
                connection.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_action_proposals_room_status
                    ON action_proposals(room_reference, status)
                    """
                )
                connection.commit()
        except sqlite3.Error as exc:
            raise ProposalRepositoryError(f"Could not initialize the proposal repository: {exc}") from exc
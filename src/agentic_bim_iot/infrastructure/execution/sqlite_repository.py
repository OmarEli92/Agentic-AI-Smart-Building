import sqlite3
from pathlib import Path
from threading import Lock
from agentic_bim_iot.application.interfaces.execution_repository import ExecutionRepositoryError
from agentic_bim_iot.domain.execution import ExecutionResult


class SQLiteExecutionRepository:
    """The implementation of the Execution Repository"""
    def __init__(self, database_path: str) -> None:
        self._database_path = database_path
        self._lock = Lock()
        path = Path(database_path)
        if path.parent != Path("."):
            path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    
    def _initialize(self) -> None:
        try:
            with sqlite3.connect(self._database_path) as connection:
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS execution_results (
                        execution_id TEXT PRIMARY KEY,
                        command_id TEXT NOT NULL UNIQUE,
                        proposal_id TEXT,
                        actuator_guid TEXT NOT NULL,
                        status TEXT NOT NULL,
                        started_at_ms INTEGER NOT NULL,
                        completed_at_ms INTEGER NOT NULL,
                        payload TEXT NOT NULL
                    )
                    """
                )
                connection.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_execution_results_completed
                    ON execution_results(completed_at_ms DESC)
                    """
                )
                connection.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_execution_results_proposal
                    ON execution_results(proposal_id, started_at_ms ASC)
                    """
                )
                connection.commit()
        except sqlite3.Error as exc:
            raise ExecutionRepositoryError(f"Could not initialize the execution repository: {exc}") from exc


    def save(self, execution: ExecutionResult) -> None:
        try:
            with self._lock:
                with sqlite3.connect(self._database_path) as connection:
                    connection.execute(
                        """
                        INSERT INTO execution_results (
                            execution_id,
                            command_id,
                            proposal_id,
                            actuator_guid,
                            status,
                            started_at_ms,
                            completed_at_ms,
                            payload
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            execution.execution_id,
                            execution.command_id,
                            execution.proposal_id,
                            execution.actuator_guid,
                            execution.status.value,
                            execution.started_at_ms,
                            execution.completed_at_ms,
                            execution.model_dump_json(),
                        ),
                    )
                    connection.commit()
        except sqlite3.IntegrityError as exc:
            raise ExecutionRepositoryError(f"Execution '{execution.execution_id}' or command '{execution.command_id}' is already persisted.") from exc
        except sqlite3.Error as exc:
            raise ExecutionRepositoryError(f"Could not save the execution result: {exc}") from exc

    def get(self, execution_id: str) -> ExecutionResult | None:
        return self._get_one("SELECT payload FROM execution_results WHERE execution_id = ?", (execution_id,))


    def get_by_command_id(self, command_id: str) -> ExecutionResult | None:
        return self._get_one("SELECT payload FROM execution_results WHERE command_id = ?", (command_id,))


    def get_latest(self) -> ExecutionResult | None:
        return self._get_one("SELECT payload FROM execution_results ORDER BY completed_at_ms DESC LIMIT 1", ())


    def list_by_proposal(self, proposal_id: str) -> list[ExecutionResult]:
        try:
            with self._lock:
                with sqlite3.connect(self._database_path) as connection:
                    rows = connection.execute(
                        "SELECT payload FROM execution_results WHERE proposal_id = ? ORDER BY started_at_ms ASC",
                        (proposal_id,),
                    ).fetchall()
        except sqlite3.Error as exc:
            raise ExecutionRepositoryError(f"Could not retrieve proposal executions: {exc}") from exc
        return [ExecutionResult.model_validate_json(row[0]) for row in rows]


    def _get_one(self, query: str, parameters: tuple[object, ...]) -> ExecutionResult | None:
        try:
            with self._lock:
                with sqlite3.connect(self._database_path) as connection:
                    row = connection.execute(query, parameters).fetchone()
        except sqlite3.Error as exc:
            raise ExecutionRepositoryError(f"Could not retrieve the execution result: {exc}") from exc
        if row is None:
            return None
        return ExecutionResult.model_validate_json(row[0])

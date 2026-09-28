"""Persistent SQLite-backed Pending Approval Store cho luồng Human-in-the-loop (Component 1.5).

Lưu trữ và quản lý các truy vấn bị tạm dừng do vượt ngưỡng chi phí hoặc rủi ro dữ liệu,
sử dụng SQLite database để đảm bảo tính bền vững (survives process restart) và chia sẻ
dữ liệu giữa nhiều worker processes trên cùng một host hoặc container có shared volume.

Ranh giới kiến trúc triển khai (Deployment Architecture Boundaries):
- Single-Node Multi-Worker (Mặc định): Sử dụng SQLite với WAL mode (Write-Ahead Logging),
  hỗ trợ đa tiến trình (multiple workers/processes) an toàn qua POSIX file locking và busy_timeout.
- Multi-Node Distributed Cluster: Đối với môi trường triển khai nhiều host/nodes vật lý
  độc lập không có shared POSIX filesystem tương thích SQLite WAL, khuyến nghị sử dụng
  database tập trung (PostgreSQL / Redis) làm backend store.
"""

from __future__ import annotations

import contextlib
import json
import logging
import secrets
import sqlite3
import threading
import time
import uuid
from collections.abc import Generator
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from src.models.rbac import UserContext

logger = logging.getLogger(__name__)


def _get_default_db_path() -> Path:
    try:
        from src.config import get_settings

        return Path(get_settings().pending_approvals_db_path).resolve()
    except Exception:  # noqa: BLE001
        return Path("./data/pending_approvals.sqlite").resolve()


DEFAULT_DB_PATH = _get_default_db_path()


class PendingApproval(BaseModel):
    """Thông tin chi tiết một truy vấn đang chờ phê duyệt từ quản trị viên."""

    approval_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    sql: str
    task_id: str | None = None
    plan_id: str | None = None
    question_hash: str | None = None
    reason: str | None = None
    estimated_bytes: int = 0
    tables_used: list[str] = Field(default_factory=list)
    user_context: UserContext | None = None
    status: str = "PENDING"  # PENDING | PROCESSING | APPROVED | REJECTED | FAILED
    created_at: float = Field(default_factory=time.time)
    rejection_reason: str | None = None
    execution_result: dict[str, Any] | None = None
    consumed: bool = False
    consumed_at: float | None = None
    processing_started_at: float | None = None
    processing_owner: str | None = None


class SQLitePendingApprovalStore:
    """Kho lưu trữ phê duyệt HITL và sở hữu phiên bền vững trên SQLite với WAL mode."""

    def __init__(self, db_path: Path | str | None = None):
        if db_path == ":memory:":
            self.db_path: Path | str = ":memory:"
        elif db_path is not None:
            self.db_path = Path(db_path).resolve()
        else:
            self.db_path = _get_default_db_path()
        self._lock = threading.Lock()
        self._ensure_db()

    @contextlib.contextmanager
    def _connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Tạo kết nối SQLite an toàn và luôn đóng giải phóng file handle."""
        if self.db_path != ":memory:":
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(
                str(self.db_path), timeout=30.0, check_same_thread=False
            )
            conn.execute("PRAGMA journal_mode=WAL;")
        else:
            conn = sqlite3.connect(":memory:", check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _ensure_db(self) -> None:
        """Tạo bảng và indexes nếu chưa tồn tại, tự động nâng cấp schema nếu thiếu cột."""
        with self._lock, self._connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS pending_approvals (
                    approval_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    task_id TEXT,
                    plan_id TEXT,
                    question_hash TEXT,
                    sql TEXT NOT NULL,
                    reason TEXT,
                    estimated_bytes INTEGER NOT NULL DEFAULT 0,
                    tables_used TEXT NOT NULL DEFAULT '[]',
                    user_context TEXT,
                    status TEXT NOT NULL DEFAULT 'PENDING',
                    created_at REAL NOT NULL,
                    rejection_reason TEXT,
                    execution_result TEXT,
                    consumed INTEGER NOT NULL DEFAULT 0,
                    consumed_at REAL,
                    processing_started_at REAL,
                    processing_owner TEXT
                );
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS session_ownership (
                    session_id TEXT PRIMARY KEY,
                    owner_user_id TEXT NOT NULL,
                    session_token TEXT,
                    is_anonymous INTEGER NOT NULL DEFAULT 0,
                    created_at REAL NOT NULL,
                    last_accessed_at REAL NOT NULL
                );
                """
            )
            # Nâng cấp các cột nếu DB đã tồn tại từ trước trước khi tạo index
            self._migrate_columns_if_missing(conn)

            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_pending_session_status
                ON pending_approvals(session_id, status);
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_pending_task
                ON pending_approvals(task_id);
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_pending_plan_consumed
                ON pending_approvals(plan_id, consumed);
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_session_owner
                ON session_ownership(owner_user_id);
                """
            )
            conn.commit()

    def _migrate_columns_if_missing(self, conn: sqlite3.Connection) -> None:
        """Thêm các cột mới an toàn vào bảng cũ nếu chưa tồn tại."""

        def _add_col(table: str, col_name: str, col_type: str) -> None:
            info = conn.execute(f"PRAGMA table_info({table});").fetchall()
            existing = [row["name"] for row in info]
            if col_name not in existing:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type};")

        _add_col("session_ownership", "session_token", "TEXT")
        _add_col("pending_approvals", "plan_id", "TEXT")
        _add_col("pending_approvals", "question_hash", "TEXT")
        _add_col("pending_approvals", "consumed", "INTEGER NOT NULL DEFAULT 0")
        _add_col("pending_approvals", "consumed_at", "REAL")
        _add_col("pending_approvals", "processing_started_at", "REAL")
        _add_col("pending_approvals", "processing_owner", "TEXT")

    def register_or_verify_session(
        self,
        session_id: str,
        user_id: str,
        session_token: str | None = None,
        is_admin: bool = False,
    ) -> tuple[bool, str, str | None]:
        """Xác minh hoặc đăng ký quyền sở hữu phiên trong SQLite bền vững kèm Session Secret Token.

        Quy tắc:
        - Nếu session chưa tồn tại: đăng ký user_id là chủ sở hữu, sinh session_token ngẫu nhiên.
        - Nếu session đã tồn tại:
          - is_admin = True: luôn cho phép truy cập.
          - Nếu session_token được cung cấp và khớp với token của phiên:
            cho phép truy cập và cập nhật last_accessed_at.
          - Nếu session_token không khớp hoặc thiếu (kể cả khi giả mạo đúng user_id):
            từ chối truy cập (HTTP 403 Forbidden).

        Returns:
            tuple[bool, str, str | None]: (is_allowed, error_message, session_token)
        """
        now = time.time()
        with self._lock, self._connection() as conn:
            row = conn.execute(
                "SELECT session_id, owner_user_id, session_token, is_anonymous FROM session_ownership WHERE session_id = ?",
                (session_id,),
            ).fetchone()

            if not row:
                new_token = secrets.token_urlsafe(32)
                is_anon = 1 if user_id == "anonymous_user" else 0
                conn.execute(
                    """
                    INSERT INTO session_ownership (session_id, owner_user_id, session_token, is_anonymous, created_at, last_accessed_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (session_id, user_id, new_token, is_anon, now, now),
                )
                conn.commit()
                return True, "", new_token

            stored_token = row["session_token"]
            owner_user_id = row["owner_user_id"]

            if is_admin:
                conn.execute(
                    "UPDATE session_ownership SET last_accessed_at = ? WHERE session_id = ?",
                    (now, session_id),
                )
                conn.commit()
                return True, "", stored_token

            # Đảm bảo phiên luôn có session_token
            if not stored_token:
                stored_token = secrets.token_urlsafe(32)
                conn.execute(
                    "UPDATE session_ownership SET session_token = ? WHERE session_id = ?",
                    (stored_token, session_id),
                )
                conn.commit()

            # Xác thực Session Token
            if session_token and secrets.compare_digest(session_token, stored_token):
                conn.execute(
                    "UPDATE session_ownership SET last_accessed_at = ? WHERE session_id = ?",
                    (now, session_id),
                )
                conn.commit()
                return True, "", stored_token

            # Nếu khác chủ sở hữu
            if owner_user_id != user_id:
                return (
                    False,
                    f"Phiên làm việc '{session_id}' thuộc quyền sở hữu của người dùng khác. Bạn không có quyền truy cập.",
                    None,
                )

            # Đúng user_id nhưng thiếu hoặc sai session_token
            return (
                False,
                f"Session Token không hợp lệ hoặc thiếu cho phiên '{session_id}'. Vui lòng gửi kèm X-Session-Token để xác thực quyền sở hữu phiên.",
                None,
            )

    def save(self, approval: PendingApproval) -> PendingApproval:
        """Lưu hoặc cập nhật một pending approval vào database."""
        with self._lock, self._connection() as conn:
            user_ctx_json = (
                approval.user_context.model_dump_json()
                if approval.user_context
                else None
            )
            tables_used_json = json.dumps(approval.tables_used)
            exec_res_json = (
                json.dumps(approval.execution_result)
                if approval.execution_result
                else None
            )

            conn.execute(
                """
                INSERT OR REPLACE INTO pending_approvals (
                    approval_id, session_id, task_id, plan_id, question_hash, sql, reason,
                    estimated_bytes, tables_used, user_context, status,
                    created_at, rejection_reason, execution_result,
                    consumed, consumed_at, processing_started_at, processing_owner
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    approval.approval_id,
                    approval.session_id,
                    approval.task_id,
                    approval.plan_id,
                    approval.question_hash,
                    approval.sql,
                    approval.reason,
                    approval.estimated_bytes,
                    tables_used_json,
                    user_ctx_json,
                    approval.status,
                    approval.created_at,
                    approval.rejection_reason,
                    exec_res_json,
                    1 if approval.consumed else 0,
                    approval.consumed_at,
                    approval.processing_started_at,
                    approval.processing_owner,
                ),
            )
            conn.commit()
        return approval

    def get(
        self,
        session_id: str | None = None,
        task_id: str | None = None,
        approval_id: str | None = None,
        plan_id: str | None = None,
        question_hash: str | None = None,
        status: str | None = None,
        consumed: bool | None = None,
    ) -> PendingApproval | None:
        """Tra cứu một pending approval với đầy đủ bộ lọc an toàn."""
        with self._lock, self._connection() as conn:
            query = "SELECT * FROM pending_approvals WHERE 1=1"
            params: list[Any] = []

            if approval_id:
                query += " AND approval_id = ?"
                params.append(approval_id)
            if session_id:
                query += " AND session_id = ?"
                params.append(session_id)
            if task_id:
                query += " AND task_id = ?"
                params.append(task_id)
            if plan_id:
                query += " AND plan_id = ?"
                params.append(plan_id)
            if question_hash:
                query += " AND question_hash = ?"
                params.append(question_hash)
            if status:
                query += " AND status = ?"
                params.append(status)
            if consumed is not None:
                query += " AND consumed = ?"
                params.append(1 if consumed else 0)

            query += " ORDER BY created_at DESC LIMIT 1"
            row = conn.execute(query, params).fetchone()
            if not row:
                return None

            return self._row_to_model(row)

    def consume(self, approval_id: str) -> bool:
        """Atomic consume: đánh dấu approval đã được hydrate vào analysis task, chống tái sử dụng stale result."""
        now = time.time()
        with self._lock, self._connection() as conn:
            cursor = conn.execute(
                "UPDATE pending_approvals SET consumed = 1, consumed_at = ? WHERE approval_id = ? AND consumed = 0",
                (now, approval_id),
            )
            conn.commit()
            return cursor.rowcount > 0

    def claim_for_processing(
        self,
        approval_id: str,
        session_id: str | None = None,
        worker_id: str | None = None,
        lease_timeout: float | None = None,
        lease_timeout_seconds: float | None = None,
    ) -> tuple[bool, PendingApproval | None, str]:
        """Cơ chế nguyên tử Compare-And-Set kèm Lease Timeout tự phục hồi (Self-Healing Zombie Lock)."""
        from src.config import get_settings

        now = time.time()
        timeout_arg = (
            lease_timeout if lease_timeout is not None else lease_timeout_seconds
        )
        effective_lease = (
            timeout_arg
            if timeout_arg is not None
            else getattr(get_settings(), "hitl_lease_timeout_seconds", 60)
        )

        with self._lock, self._connection() as conn:
            query = "SELECT * FROM pending_approvals WHERE approval_id = ?"
            params: list[Any] = [approval_id]
            if session_id:
                query += " AND session_id = ?"
                params.append(session_id)

            row = conn.execute(query, params).fetchone()
            if not row:
                return False, None, "NOT_FOUND"

            approval = self._row_to_model(row)
            if approval.status == "APPROVED":
                return False, approval, "ALREADY_APPROVED"
            if approval.status == "REJECTED":
                return False, approval, "ALREADY_REJECTED"
            if approval.status == "FAILED":
                return False, approval, "ALREADY_FAILED"

            if approval.status == "PROCESSING":
                started_at = approval.processing_started_at or 0
                if now - started_at > effective_lease:
                    logger.warning(
                        "Approval '%s' bị kẹt PROCESSING quá lease timeout (%ss). Tiến hành reclaim quyền xử lý.",
                        approval_id,
                        effective_lease,
                    )
                    update_query = (
                        "UPDATE pending_approvals SET status = 'PROCESSING', "
                        "processing_started_at = ?, processing_owner = ? "
                        "WHERE approval_id = ? AND status = 'PROCESSING'"
                    )
                    cursor = conn.execute(
                        update_query,
                        [now, worker_id or "reclaimed_worker", approval_id],
                    )
                    conn.commit()
                    if cursor.rowcount > 0:
                        approval.processing_started_at = now
                        approval.processing_owner = worker_id or "reclaimed_worker"
                        return True, approval, "CLAIMED"
                return False, approval, "IN_PROGRESS"

            update_query = (
                "UPDATE pending_approvals SET status = 'PROCESSING', "
                "processing_started_at = ?, processing_owner = ? "
                "WHERE approval_id = ? AND status = 'PENDING'"
            )
            update_params: list[Any] = [
                now,
                worker_id or "active_worker",
                approval_id,
            ]
            if session_id:
                update_query += " AND session_id = ?"
                update_params.append(session_id)

            cursor = conn.execute(update_query, update_params)
            conn.commit()

            if cursor.rowcount > 0:
                approval.status = "PROCESSING"
                approval.processing_started_at = now
                approval.processing_owner = worker_id or "active_worker"
                return True, approval, "CLAIMED"
            else:
                row_again = conn.execute(query, params).fetchone()
                latest = self._row_to_model(row_again) if row_again else approval
                return False, latest, "IN_PROGRESS"

    def resolve(
        self,
        session_id: str,
        approved: bool,
        task_id: str | None = None,
        approval_id: str | None = None,
        rejection_reason: str | None = None,
        execution_result: dict[str, Any] | None = None,
        status: str | None = None,
    ) -> PendingApproval | None:
        """Cập nhật trạng thái phê duyệt và lưu trữ kết quả thực thi bền vững."""
        approval = self.get(
            session_id=session_id, task_id=task_id, approval_id=approval_id
        )
        if not approval:
            return None

        if status:
            approval.status = status
        else:
            approval.status = "APPROVED" if approved else "REJECTED"
        approval.rejection_reason = rejection_reason
        approval.execution_result = execution_result
        return self.save(approval)

    def remove(
        self,
        session_id: str,
        task_id: str | None = None,
        approval_id: str | None = None,
    ) -> PendingApproval | None:
        """Xóa mục chờ duyệt khỏi database."""
        approval = self.get(
            session_id=session_id, task_id=task_id, approval_id=approval_id
        )
        if not approval:
            return None

        with self._lock, self._connection() as conn:
            conn.execute(
                "DELETE FROM pending_approvals WHERE approval_id = ?",
                (approval.approval_id,),
            )
            conn.commit()
        return approval

    def clear(self) -> None:
        """Xóa toàn bộ pending store và session ownership (phục vụ test)."""
        with self._lock, self._connection() as conn:
            conn.execute("DELETE FROM pending_approvals")
            conn.execute("DELETE FROM session_ownership")
            conn.commit()

    @staticmethod
    def _row_to_model(row: sqlite3.Row) -> PendingApproval:
        user_ctx = None
        if row["user_context"]:
            try:
                user_ctx = UserContext.model_validate_json(row["user_context"])
            except Exception:  # noqa: BLE001
                user_ctx = None

        tables_used = []
        if row["tables_used"]:
            try:
                tables_used = json.loads(row["tables_used"])
            except Exception:  # noqa: BLE001
                tables_used = []

        exec_res = None
        if row["execution_result"]:
            try:
                exec_res = json.loads(row["execution_result"])
            except Exception:  # noqa: BLE001
                exec_res = None

        keys = row.keys()
        return PendingApproval(
            approval_id=row["approval_id"],
            session_id=row["session_id"],
            task_id=row["task_id"] if "task_id" in keys else None,
            plan_id=row["plan_id"] if "plan_id" in keys else None,
            question_hash=row["question_hash"] if "question_hash" in keys else None,
            sql=row["sql"],
            reason=row["reason"],
            estimated_bytes=row["estimated_bytes"],
            tables_used=tables_used,
            user_context=user_ctx,
            status=row["status"],
            created_at=row["created_at"],
            rejection_reason=row["rejection_reason"],
            execution_result=exec_res,
            consumed=bool(row["consumed"])
            if "consumed" in keys and row["consumed"]
            else False,
            consumed_at=row["consumed_at"] if "consumed_at" in keys else None,
            processing_started_at=row["processing_started_at"]
            if "processing_started_at" in keys
            else None,
            processing_owner=row["processing_owner"]
            if "processing_owner" in keys
            else None,
        )


# Singleton store instance
_DEFAULT_STORE: SQLitePendingApprovalStore | None = None


def get_pending_store() -> SQLitePendingApprovalStore:
    """Trả về singleton SQLitePendingApprovalStore dùng chung."""
    global _DEFAULT_STORE
    if _DEFAULT_STORE is None:
        _DEFAULT_STORE = SQLitePendingApprovalStore()
    return _DEFAULT_STORE


def save_pending_approval(
    session_id: str,
    sql: str,
    reason: str | None = None,
    estimated_bytes: int = 0,
    tables_used: list[str] | None = None,
    task_id: str | None = None,
    plan_id: str | None = None,
    question_hash: str | None = None,
    user_context: UserContext | None = None,
    approval_id: str | None = None,
) -> PendingApproval:
    """Lưu một truy vấn vào danh sách chờ phê duyệt (SQLite)."""
    approval = PendingApproval(
        approval_id=approval_id or str(uuid.uuid4()),
        session_id=session_id,
        sql=sql,
        reason=reason,
        estimated_bytes=estimated_bytes,
        tables_used=tables_used or [],
        task_id=task_id,
        plan_id=plan_id,
        question_hash=question_hash,
        user_context=user_context,
        status="PENDING",
    )
    return get_pending_store().save(approval)


def get_pending_approval(
    session_id: str | None = None,
    task_id: str | None = None,
    approval_id: str | None = None,
    plan_id: str | None = None,
    question_hash: str | None = None,
    status: str | None = None,
    consumed: bool | None = None,
) -> PendingApproval | None:
    """Truy xuất thông tin truy vấn chờ duyệt."""
    return get_pending_store().get(
        session_id=session_id,
        task_id=task_id,
        approval_id=approval_id,
        plan_id=plan_id,
        question_hash=question_hash,
        status=status,
        consumed=consumed,
    )


def consume_pending_approval(approval_id: str) -> bool:
    """Đánh dấu approval đã được hydrate vào analysis task."""
    return get_pending_store().consume(approval_id)


def resolve_pending_approval(
    session_id: str,
    approved: bool,
    task_id: str | None = None,
    approval_id: str | None = None,
    rejection_reason: str | None = None,
    execution_result: dict[str, Any] | None = None,
    status: str | None = None,
) -> PendingApproval | None:
    """Cập nhật trạng thái phê duyệt và giải phóng/lưu kết quả sau khi xử lý."""
    return get_pending_store().resolve(
        session_id=session_id,
        approved=approved,
        task_id=task_id,
        approval_id=approval_id,
        rejection_reason=rejection_reason,
        execution_result=execution_result,
        status=status,
    )


def remove_pending_approval(
    session_id: str,
    task_id: str | None = None,
    approval_id: str | None = None,
) -> PendingApproval | None:
    """Xóa mục chờ duyệt khỏi database."""
    return get_pending_store().remove(
        session_id=session_id,
        task_id=task_id,
        approval_id=approval_id,
    )


def clear_all_pending_approvals() -> None:
    """Xóa toàn bộ pending store và session ownership (phục vụ test)."""
    get_pending_store().clear()


def claim_pending_approval(
    approval_id: str,
    session_id: str | None = None,
    worker_id: str | None = None,
    lease_timeout: float | None = None,
) -> tuple[bool, PendingApproval | None, str]:
    """Cơ chế nguyên tử Compare-And-Set claim quyền xử lý truy vấn đang chờ duyệt."""
    return get_pending_store().claim_for_processing(
        approval_id=approval_id,
        session_id=session_id,
        worker_id=worker_id,
        lease_timeout=lease_timeout,
    )


def register_or_verify_session(
    session_id: str,
    user_id: str,
    session_token: str | None = None,
    is_admin: bool = False,
) -> tuple[bool, str, str | None]:
    """Xác minh hoặc đăng ký quyền sở hữu phiên làm việc trong SQLite bền vững kèm Session Token."""
    return get_pending_store().register_or_verify_session(
        session_id=session_id,
        user_id=user_id,
        session_token=session_token,
        is_admin=is_admin,
    )

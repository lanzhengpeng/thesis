"""
智能体会话存储
===============

使用 SQLite 持久化需求分析会话，支持多轮问答、状态追踪与生成结果归档。
所有 JSON 字段在写入时序列化、读取时反序列化。
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from .schemas import ArchitectureDoc, RequirementsDoc


# 数据库文件放在项目根目录的 database/ 下
DB_DIR = Path(__file__).resolve().parent.parent.parent / "database"
DB_PATH = DB_DIR / "agent_sessions.db"

_DB_LOCK = threading.Lock()


_INIT_SQL = """
CREATE TABLE IF NOT EXISTS requirement_sessions (
    session_id TEXT PRIMARY KEY,
    status TEXT NOT NULL DEFAULT 'requirements_gathering',
    task TEXT NOT NULL,
    current_questions TEXT,
    answers TEXT,
    requirements_doc TEXT,
    architecture_doc TEXT,
    generated_files TEXT,
    written TEXT,
    checks TEXT,
    reload_report TEXT,
    logs TEXT,
    result TEXT,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sessions_status ON requirement_sessions(status);
CREATE INDEX IF NOT EXISTS idx_sessions_updated_at ON requirement_sessions(updated_at);
"""


def _ensure_db_dir() -> None:
    """确保数据库目录存在。"""
    DB_DIR.mkdir(parents=True, exist_ok=True)


def _new_conn() -> sqlite3.Connection:
    """创建并返回一个 SQLite 连接，启用行工厂与类型检测。"""
    _ensure_db_dir()
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_schema() -> None:
    """初始化会话表与索引。"""
    with _DB_LOCK, _new_conn() as conn:
        conn.executescript(_INIT_SQL)


def _json_dump(value: Any) -> Optional[str]:
    """将任意值序列化为 JSON 字符串；None 保持 None。"""
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False)


def _json_load(value: Optional[str]) -> Any:
    """将 JSON 字符串反序列化；None 保持 None。"""
    if value is None:
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return None


def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    """将 SQLite 行转换为字典，并自动反序列化 JSON 字段。"""
    result: Dict[str, Any] = dict(row)
    json_fields = {
        "current_questions",
        "answers",
        "requirements_doc",
        "architecture_doc",
        "generated_files",
        "written",
        "checks",
        "reload_report",
        "logs",
    }
    for field in json_fields:
        result[field] = _json_load(result.get(field))
    return result


def create_session(
    task: str,
    questions: Optional[List[Dict[str, str]]] = None,
) -> str:
    """
    创建一个新的需求分析会话。

    参数：
        task: 用户原始任务描述。
        questions: 首轮需要向用户提出的问题列表。

    返回：
        新会话的 session_id。
    """
    init_schema()
    session_id = uuid.uuid4().hex
    now = time.time()
    with _DB_LOCK, _new_conn() as conn:
        conn.execute(
            """
            INSERT INTO requirement_sessions
            (session_id, status, task, current_questions, answers, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                "requirements_gathering",
                task,
                _json_dump(questions),
                _json_dump([]),
                now,
                now,
            ),
        )
    return session_id


def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    """
    获取指定会话的完整状态。

    参数：
        session_id: 会话 ID。

    返回：
        会话字典；不存在时返回 None。
    """
    init_schema()
    with _DB_LOCK, _new_conn() as conn:
        row = conn.execute(
            "SELECT * FROM requirement_sessions WHERE session_id = ?",
            (session_id,),
        ).fetchone()
    if row is None:
        return None
    return _row_to_dict(row)


def update_session(
    session_id: str,
    status: Optional[str] = None,
    questions: Optional[List[Dict[str, str]]] = None,
    answers: Optional[List[Dict[str, str]]] = None,
    requirements_doc: Optional[RequirementsDoc] = None,
    architecture_doc: Optional[ArchitectureDoc] = None,
    generated_files: Optional[Dict[str, str]] = None,
    written: Optional[List[str]] = None,
    checks: Optional[Dict[str, Any]] = None,
    reload_report: Optional[Dict[str, Any]] = None,
    logs: Optional[List[str]] = None,
    result: Optional[Dict[str, Any]] = None,
) -> bool:
    """
    更新会话的指定字段。

    参数：
        session_id: 会话 ID。
        其余字段为可选项，传入非 None 时更新。

    返回：
        是否成功更新（会话存在时为 True）。
    """
    init_schema()
    updates: Dict[str, Any] = {}
    if status is not None:
        updates["status"] = status
    if questions is not None:
        updates["current_questions"] = _json_dump(questions)
    if answers is not None:
        updates["answers"] = _json_dump(answers)
    if requirements_doc is not None:
        updates["requirements_doc"] = _json_dump(requirements_doc)
    if architecture_doc is not None:
        updates["architecture_doc"] = _json_dump(architecture_doc)
    if generated_files is not None:
        updates["generated_files"] = _json_dump(generated_files)
    if written is not None:
        updates["written"] = _json_dump(written)
    if checks is not None:
        updates["checks"] = _json_dump(checks)
    if reload_report is not None:
        updates["reload_report"] = _json_dump(reload_report)
    if logs is not None:
        updates["logs"] = _json_dump(logs)
    if result is not None:
        updates["result"] = _json_dump(result)

    if not updates:
        return False

    updates["updated_at"] = time.time()
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [session_id]

    with _DB_LOCK, _new_conn() as conn:
        cursor = conn.execute(
            f"UPDATE requirement_sessions SET {set_clause} WHERE session_id = ?",
            values,
        )
    return cursor.rowcount > 0


def append_logs(session_id: str, new_logs: List[str]) -> bool:
    """
    向会话追加日志。

    参数：
        session_id: 会话 ID。
        new_logs: 待追加的日志条目列表。

    返回：
        是否成功追加。
    """
    session = get_session(session_id)
    if session is None:
        return False
    existing = session.get("logs") or []
    existing.extend(new_logs)
    return update_session(session_id, logs=existing)

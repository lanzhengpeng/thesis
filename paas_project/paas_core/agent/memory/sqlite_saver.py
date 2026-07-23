from pathlib import Path

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from paas_core.agent.core.config import settings


def create_sqlite_saver() -> AsyncSqliteSaver:
    db_path = Path(settings.CHECKPOINT_DB)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return AsyncSqliteSaver.from_conn_string(str(db_path))

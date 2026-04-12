"""Project Overwatch package bootstrap."""

from pathlib import Path
import os

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_RUNTIME_ROOT = _PROJECT_ROOT / ".runtime"
_LOCAL_APPDATA = _RUNTIME_ROOT / "localappdata"
_APPDATA = _RUNTIME_ROOT / "appdata"
_CREWAI_STORAGE = _RUNTIME_ROOT / "crewai_storage"

for _path in (_RUNTIME_ROOT, _LOCAL_APPDATA, _APPDATA, _CREWAI_STORAGE):
    _path.mkdir(parents=True, exist_ok=True)

# Keep CrewAI's internal SQLite storage inside the project workspace.
# This avoids readonly AppData failures in sandboxed or restricted environments.
os.environ["LOCALAPPDATA"] = str(_LOCAL_APPDATA)
os.environ.setdefault("APPDATA", str(_APPDATA))
os.environ["CREWAI_STORAGE_DIR"] = "ProjectOverwatch"


def _workspace_db_storage_path() -> str:
    """Return the workspace-local path for CrewAI SQLite storage."""
    _CREWAI_STORAGE.mkdir(parents=True, exist_ok=True)
    return str(_CREWAI_STORAGE)


try:
    from crewai.utilities import paths as _crewai_paths
    from crewai.flow.persistence import sqlite as _flow_sqlite
    from crewai.knowledge.storage import knowledge_storage as _knowledge_storage
    from crewai.memory.storage import kickoff_task_outputs_storage as _kickoff_storage
    from crewai.memory.storage import ltm_sqlite_storage as _ltm_storage
    from crewai.memory.storage import rag_storage as _rag_storage

    _crewai_paths.db_storage_path = _workspace_db_storage_path
    _flow_sqlite.db_storage_path = _workspace_db_storage_path
    _knowledge_storage.db_storage_path = _workspace_db_storage_path
    _kickoff_storage.db_storage_path = _workspace_db_storage_path
    _ltm_storage.db_storage_path = _workspace_db_storage_path
    _rag_storage.db_storage_path = _workspace_db_storage_path
except Exception:
    # Import verification still works even if some optional CrewAI modules
    # change internally; the runtime will fall back to CrewAI defaults.
    pass

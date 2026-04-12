import json, uuid
from datetime import datetime
from pathlib import Path
from typing import Optional
import chromadb
from rich.console import Console
from .config import CONFIDENCE_THRESHOLD
from .schemas import IntelligenceReport

console = Console()
_MEMORY_DIR = Path(__file__).parent.parent / "memory_db"

class CognitiveMemory:
    def __init__(self, collection_name: str = "intel_reports"):
        _MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=str(_MEMORY_DIR))
        self.collection = self.client.get_or_create_collection(
            name=collection_name, metadata={"hnsw:space": "cosine"}
        )

    def store_report(self, report: IntelligenceReport, repo: str) -> str:
        doc_id = f"{repo}::{datetime.now().strftime('%Y%m%d_%H%M%S')}::{uuid.uuid4().hex[:8]}"
        embedding_text = f"Summary: {report.summary}"
        metadata = {
            "repo": repo, "timestamp": datetime.now().isoformat(),
            "confidence": report.confidence_score,
            "requires_retry": report.requires_retry,
            "architecture_changes": json.dumps(report.architecture_changes)
        }
        self.collection.add(documents=[embedding_text], metadatas=[metadata], ids=[doc_id])
        return doc_id

    def query_history(self, query: str, repo: str, n_results: int = 3) -> str:
        try:
            total = self.collection.count()
            if total == 0:
                return "No historical data."
            res = self.collection.query(query_texts=[query], n_results=min(n_results, total), where={"repo": repo})
            docs = res.get("documents", [[]])[0]
            metadatas = res.get("metadatas", [[]])[0]
            if not docs:
                return "No historical data."

            valid_entries = []
            for doc, metadata in zip(docs, metadatas):
                confidence = float(metadata.get("confidence", 0.0))
                requires_retry = bool(metadata.get("requires_retry", False))
                if confidence < CONFIDENCE_THRESHOLD or requires_retry:
                    continue

                timestamp = metadata.get("timestamp", "unknown")
                changes_raw = metadata.get("architecture_changes", "[]")
                try:
                    changes = json.loads(changes_raw)
                except Exception:
                    changes = []

                valid_entries.append({
                    "timestamp": timestamp,
                    "confidence": confidence,
                    "summary": doc,
                    "changes": changes,
                })

            if not valid_entries:
                return "No validated historical data."

            valid_entries.sort(key=lambda entry: entry["timestamp"], reverse=True)

            lines = [
                "Historical context only. Do not treat history as evidence of current changes unless current commits, docs, or cited URLs corroborate it."
            ]
            for entry in valid_entries:
                lines.append(
                    f"- {entry['timestamp']} | confidence {entry['confidence']:.2f} | {entry['summary']}"
                )
                if entry["changes"]:
                    lines.append(
                        "  Past validated changes: " + ", ".join(entry["changes"][:3])
                    )
            return "History:\n" + "\n".join(lines)
        except Exception as e:
            return f"Memory query failed: {e}"

    def get_report_count(self, repo: Optional[str] = None) -> int:
        if repo is None: return self.collection.count()
        return len(self.collection.get(where={"repo": repo}).get("ids", []))

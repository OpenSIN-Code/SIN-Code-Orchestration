"""Shared Context Store für dezentrale Agenten-Koordination."""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Any, Optional

import msgspec
from pydantic import BaseModel, Field


class ContextStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    VERIFIED = "verified"


@dataclass
class ContextEntry:
    """Ein Eintrag im Shared Context Store."""
    id: str
    task_id: str
    agent_id: str
    role: str
    status: ContextStatus
    input_data: dict[str, Any]
    output_data: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)
    dependencies: list[str] = field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps(asdict(self))

    @classmethod
    def from_json(cls, data: str) -> "ContextEntry":
        d = json.loads(data)
        d["status"] = ContextStatus(d["status"])
        return cls(**d)


class SharedContextStore:
    """Persistenter, verteilter Kontext-Speicher für Agenten."""

    def __init__(self, backend: str = "memory", **kwargs):
        self.backend = backend
        self._store: dict[str, ContextEntry] = {}
        self._indexes: dict[str, dict[str, set]] = {"task_id": {}, "agent_id": {}, "status": {}}

        if backend == "redis":
            import redis
            self._redis = redis.from_url(kwargs.get("redis_url") or "redis://localhost:6379/0")
            self._namespace = kwargs.get("namespace") or "sin:ctx"
        elif backend == "sqlite":
            import sqlite3
            from pathlib import Path
            db_path = kwargs.get("db_path") or ".sin/context.db"
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
            self._db = sqlite3.connect(db_path)
            self._init_sqlite()

    def _init_sqlite(self):
        self._db.execute("""
            CREATE TABLE IF NOT EXISTS context_entries (
                id TEXT PRIMARY KEY,
                task_id TEXT,
                agent_id TEXT,
                role TEXT,
                status TEXT,
                input_data TEXT,
                output_data TEXT,
                error TEXT,
                created_at REAL,
                updated_at REAL,
                metadata TEXT,
                dependencies TEXT
            )
        """)
        self._db.execute("CREATE INDEX IF NOT EXISTS idx_task ON context_entries(task_id)")
        self._db.commit()

    def put(self, entry: ContextEntry, ttl: Optional[int] = None) -> None:
        entry.updated_at = time.time()
        if self.backend == "memory":
            self._store[entry.id] = entry
            for idx_key in ("task_id", "agent_id", "status"):
                idx_val = getattr(entry, idx_key)
                if isinstance(idx_val, ContextStatus):
                    idx_val = idx_val.value
                self._indexes[idx_key].setdefault(idx_val, set()).add(entry.id)
        elif self.backend == "redis":
            key = f"{self._namespace}:{entry.id}"
            self._redis.setex(key, ttl or 3600, entry.to_json())
            self._redis.sadd(f"{self._namespace}:idx:task:{entry.task_id}", entry.id)
        elif self.backend == "sqlite":
            self._db.execute("""
                INSERT OR REPLACE INTO context_entries
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                entry.id, entry.task_id, entry.agent_id, entry.role,
                entry.status.value, json.dumps(entry.input_data),
                json.dumps(entry.output_data) if entry.output_data else None,
                entry.error, entry.created_at, entry.updated_at,
                json.dumps(entry.metadata), json.dumps(entry.dependencies)
            ))
            self._db.commit()

    def get(self, entry_id: str) -> Optional[ContextEntry]:
        if self.backend == "memory":
            return self._store.get(entry_id)
        elif self.backend == "redis":
            data = self._redis.get(f"{self._namespace}:{entry_id}")
            return ContextEntry.from_json(data) if data else None
        elif self.backend == "sqlite":
            cur = self._db.execute("SELECT * FROM context_entries WHERE id = ?", (entry_id,))
            row = cur.fetchone()
            if row:
                return ContextEntry(
                    id=row[0], task_id=row[1], agent_id=row[2], role=row[3],
                    status=ContextStatus(row[4]), input_data=json.loads(row[5]),
                    output_data=json.loads(row[6]) if row[6] else None,
                    error=row[7], created_at=row[8], updated_at=row[9],
                    metadata=json.loads(row[10]), dependencies=json.loads(row[11])
                )
        return None

    def query(self, task_id: Optional[str] = None, agent_id: Optional[str] = None,
              status: Optional[ContextStatus] = None) -> list[ContextEntry]:
        results = []
        if self.backend == "memory":
            candidates = list(self._store.values())
        elif self.backend == "redis":
            ids = set()
            if task_id:
                ids.update(self._redis.smembers(f"{self._namespace}:idx:task:{task_id}"))
            candidates = [self.get(i.decode() if isinstance(i, bytes) else i) for i in ids]
        elif self.backend == "sqlite":
            query = "SELECT * FROM context_entries WHERE 1=1"
            params = []
            if task_id:
                query += " AND task_id = ?"
                params.append(task_id)
            if agent_id:
                query += " AND agent_id = ?"
                params.append(agent_id)
            if status:
                query += " AND status = ?"
                params.append(status.value)
            cur = self._db.execute(query, params)
            candidates = []
            for row in cur.fetchall():
                candidates.append(ContextEntry(
                    id=row[0], task_id=row[1], agent_id=row[2], role=row[3],
                    status=ContextStatus(row[4]), input_data=json.loads(row[5]),
                    output_data=json.loads(row[6]) if row[6] else None,
                    error=row[7], created_at=row[8], updated_at=row[9],
                    metadata=json.loads(row[10]), dependencies=json.loads(row[11])
                ))
        else:
            candidates = []

        for entry in candidates:
            if entry is None:
                continue
            if task_id and entry.task_id != task_id:
                continue
            if agent_id and entry.agent_id != agent_id:
                continue
            if status and entry.status != status:
                continue
            results.append(entry)
        return results

    def update_status(self, entry_id: str, status: ContextStatus,
                      output_data: Optional[dict] = None, error: Optional[str] = None) -> None:
        entry = self.get(entry_id)
        if entry:
            entry.status = status
            if output_data:
                entry.output_data = output_data
            if error:
                entry.error = error
            self.put(entry)

    def create_entry(self, task_id: str, agent_id: str, role: str,
                     input_data: dict, dependencies: Optional[list] = None) -> ContextEntry:
        entry = ContextEntry(
            id=str(uuid.uuid4()),
            task_id=task_id,
            agent_id=agent_id,
            role=role,
            status=ContextStatus.PENDING,
            input_data=input_data,
            dependencies=dependencies or []
        )
        self.put(entry)
        return entry

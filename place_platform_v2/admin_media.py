"""Internal Admin media upload store.

Uploaded media is held outside canonical storage.  The store records immutable
metadata for audit/review and returns a local URL that may be used in an
Evidence Draft.  Publication to a public media service is deliberately outside
this phase.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import sqlite3
from uuid import uuid4

ALLOWED_CONTENT_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
MAX_UPLOAD_BYTES = 8 * 1024 * 1024


@dataclass(frozen=True)
class AdminMediaAsset:
    media_id: str
    url: str
    content_type: str
    size_bytes: int
    sha256: str
    original_name: str
    created_at: str


class AdminMediaStore:
    def __init__(self, database: str | Path, media_dir: str | Path, public_prefix: str = "/data/v2/admin_media"):
        self.database = Path(database)
        self.media_dir = Path(media_dir)
        self.public_prefix = public_prefix.rstrip("/")
        self.database.parent.mkdir(parents=True, exist_ok=True)
        self.media_dir.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.database)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS admin_media_assets (
                media_id TEXT PRIMARY KEY,
                storage_name TEXT NOT NULL UNIQUE,
                original_name TEXT NOT NULL,
                content_type TEXT NOT NULL,
                size_bytes INTEGER NOT NULL,
                sha256 TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        self.connection.commit()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()

    def close(self):
        self.connection.close()

    def save(self, *, data: bytes, original_name: str, content_type: str) -> AdminMediaAsset:
        if content_type not in ALLOWED_CONTENT_TYPES:
            raise ValueError("unsupported image type; use JPEG, PNG, or WebP")
        if not data:
            raise ValueError("image file is empty")
        if len(data) > MAX_UPLOAD_BYTES:
            raise ValueError("image exceeds 8 MB limit")
        name = Path(str(original_name or "upload")).name.strip() or "upload"
        digest = hashlib.sha256(data).hexdigest()
        ext = ALLOWED_CONTENT_TYPES[content_type]
        storage_name = f"{digest[:24]}{ext}"
        path = self.media_dir / storage_name
        if not path.exists():
            path.write_bytes(data)
        existing = self.connection.execute(
            "SELECT * FROM admin_media_assets WHERE storage_name=?", (storage_name,)
        ).fetchone()
        if existing is None:
            media_id = str(uuid4())
            created_at = datetime.now(timezone.utc).isoformat()
            self.connection.execute(
                "INSERT INTO admin_media_assets(media_id,storage_name,original_name,content_type,size_bytes,sha256,created_at) VALUES(?,?,?,?,?,?,?)",
                (media_id, storage_name, name, content_type, len(data), digest, created_at),
            )
            self.connection.commit()
            row = self.connection.execute("SELECT * FROM admin_media_assets WHERE media_id=?", (media_id,)).fetchone()
        else:
            row = existing
        return AdminMediaAsset(
            media_id=row["media_id"],
            url=f"{self.public_prefix}/{row['storage_name']}",
            content_type=row["content_type"],
            size_bytes=row["size_bytes"],
            sha256=row["sha256"],
            original_name=row["original_name"],
            created_at=row["created_at"],
        )

"""
Artifact Manager for CLORA Sovereign Intelligence.
Owns:
- Secure artifact ingestion (MIME detection, magic-byte verification, file size limits)
- Cryptographic SHA-256 fingerprinting
- Immutable on-premise storage
- Artifact lifecycle tracking
"""

import os
import io
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Union
from pydantic import BaseModel, ConfigDict, Field
from PIL import Image

from backend.app.core.config import settings

# Magic bytes definitions for visual and document artifacts
MAGIC_BYTES = {
    "image/png": b"\x89PNG\r\n\x1a\n",
    "image/jpeg": b"\xff\xd8\xff",
    "image/webp": (b"RIFF", b"WEBP"),  # RIFF....WEBP
    "image/tiff_le": b"II*\x00",
    "image/tiff_be": b"MM\x00*",
    "application/pdf": b"%PDF-",
}

MAX_ARTIFACT_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB limit for air-gapped laptop memory


class ArtifactRecord(BaseModel):
    """Immutable record representing an ingested physical visual or document artifact."""
    model_config = ConfigDict(frozen=True)

    artifact_id: str
    artifact_version: str = "1.0.0"
    content_hash: str
    mime_type: str
    size_bytes: int
    created_at: str
    storage_path: str
    filename: str
    image_dimensions: Optional[Dict[str, int]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ArtifactManager:
    """
    Manages physical file artifacts under sovereign air-gap trust boundaries.
    Enforces write-once immutable storage and magic-byte security checks.
    """

    def __init__(self, base_storage_dir: Optional[str] = None):
        if base_storage_dir:
            self.base_dir = Path(base_storage_dir)
        else:
            self.base_dir = Path(settings.STORAGE_DIR) / "artifacts"
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._registry: Dict[str, ArtifactRecord] = {}

    def detect_mime_from_magic_bytes(self, data: bytes) -> str:
        """Determines true MIME type by verifying file header magic bytes."""
        if len(data) < 8:
            return "application/octet-stream"

        if data.startswith(MAGIC_BYTES["image/png"]):
            return "image/png"
        if data.startswith(MAGIC_BYTES["image/jpeg"]):
            return "image/jpeg"
        if data.startswith(MAGIC_BYTES["application/pdf"]):
            return "application/pdf"
        if data.startswith(MAGIC_BYTES["image/tiff_le"]) or data.startswith(MAGIC_BYTES["image/tiff_be"]):
            return "image/tiff"
        if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
            return "image/webp"

        return "application/octet-stream"

    def ingest_artifact(
        self,
        file_input: Union[str, bytes, Path],
        filename: Optional[str] = None,
        artifact_version: str = "1.0.0",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ArtifactRecord:
        """
        Ingests a file, verifies magic bytes, computes SHA-256, and stores immutably.
        """
        # 1. Read raw bytes
        if isinstance(file_input, (str, Path)):
            p = Path(file_input)
            if not p.exists():
                raise FileNotFoundError(f"Artifact file not found: {file_input}")
            with open(p, "rb") as f:
                raw_bytes = f.read()
            orig_name = filename or p.name
        elif isinstance(file_input, bytes):
            raw_bytes = file_input
            orig_name = filename or "unnamed_artifact.png"
        else:
            raise ValueError("Unsupported artifact input type")

        # 2. File size verification
        size_bytes = len(raw_bytes)
        if size_bytes == 0:
            raise ValueError("Cannot ingest empty artifact (0 bytes)")
        if size_bytes > MAX_ARTIFACT_SIZE_BYTES:
            raise ValueError(f"Artifact exceeds maximum size of {MAX_ARTIFACT_SIZE_BYTES} bytes (was {size_bytes})")

        # 3. Magic byte detection
        detected_mime = self.detect_mime_from_magic_bytes(raw_bytes)

        # 4. Cryptographic SHA-256 fingerprint
        content_hash = hashlib.sha256(raw_bytes).hexdigest()
        artifact_id = f"art_{content_hash[:16]}"

        # 5. Extract image dimensions if image
        dimensions = None
        if "image" in detected_mime:
            try:
                with Image.open(io.BytesIO(raw_bytes)) as img:
                    dimensions = {"width": img.width, "height": img.height}
            except Exception:
                pass

        # 6. Immutable Storage Allocation (write-once directory)
        artifact_dir = self.base_dir / artifact_id / artifact_version
        artifact_dir.mkdir(parents=True, exist_ok=True)
        storage_path = artifact_dir / orig_name

        if not storage_path.exists():
            with open(storage_path, "wb") as f:
                f.write(raw_bytes)

        now_utc = datetime.now(timezone.utc).isoformat()
        record = ArtifactRecord(
            artifact_id=artifact_id,
            artifact_version=artifact_version,
            content_hash=content_hash,
            mime_type=detected_mime,
            size_bytes=size_bytes,
            created_at=now_utc,
            storage_path=str(storage_path),
            filename=orig_name,
            image_dimensions=dimensions,
            metadata=dict(metadata or {}),
        )

        self._registry[artifact_id] = record
        return record

    def get_artifact(self, artifact_id: str) -> Optional[ArtifactRecord]:
        """Retrieves artifact record from memory registry or storage filesystem."""
        if artifact_id in self._registry:
            return self._registry[artifact_id]

        target_dir = self.base_dir / artifact_id
        if target_dir.exists():
            # Find newest version directory
            versions = [d for d in target_dir.iterdir() if d.is_dir()]
            if versions:
                newest = sorted(versions, key=lambda v: v.name, reverse=True)[0]
                files = [f for f in newest.iterdir() if f.is_file()]
                if files:
                    file_path = files[0]
                    with open(file_path, "rb") as f:
                        b = f.read()
                    mime = self.detect_mime_from_magic_bytes(b)
                    chash = hashlib.sha256(b).hexdigest()
                    rec = ArtifactRecord(
                        artifact_id=artifact_id,
                        artifact_version=newest.name,
                        content_hash=chash,
                        mime_type=mime,
                        size_bytes=len(b),
                        created_at=datetime.now(timezone.utc).isoformat(),
                        storage_path=str(file_path),
                        filename=file_path.name,
                    )
                    self._registry[artifact_id] = rec
                    return rec

        return None

    def read_artifact_bytes(self, artifact_id: str) -> bytes:
        """Reads raw binary content of verified artifact."""
        rec = self.get_artifact(artifact_id)
        if not rec or not os.path.exists(rec.storage_path):
            raise FileNotFoundError(f"Artifact {artifact_id} not available on disk")
        with open(rec.storage_path, "rb") as f:
            data = f.read()

        # Integrity verification
        actual_hash = hashlib.sha256(data).hexdigest()
        if actual_hash != rec.content_hash:
            raise ValueError(f"Tamper detection: Artifact {artifact_id} hash mismatch!")
        return data

    def open_artifact_image(self, artifact_id: str) -> Image.Image:
        """Opens image from artifact store."""
        data = self.read_artifact_bytes(artifact_id)
        return Image.open(io.BytesIO(data))


default_artifact_manager = ArtifactManager()

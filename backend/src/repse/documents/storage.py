"""Local-disk file storage with signed, short-lived download tokens.

Layout (research.md §5 spec 001):
    {UPLOAD_ROOT}/{organization_id}/{supplier_id}/{document_id}/v{version}.{ext}

Tokens are JWS issued via itsdangerous; they encode {file_id, user_id,
organization_id, exp} and have a 5-minute TTL by default. The download endpoint
validates both the token AND the current session (tenant_id MUST match).
"""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

from itsdangerous import BadSignature, SignatureExpired, TimestampSigner, URLSafeTimedSerializer

from repse.config import Settings


@dataclass(frozen=True)
class StoredFile:
    relative_path: str
    size_bytes: int
    sha256_hex: str


class FileStore:
    def __init__(self, settings: Settings) -> None:
        self._root = settings.upload_root
        secret = settings.app_secret.get_secret_value()
        self._signer = TimestampSigner(secret, salt="repse.file-download")
        self._serializer = URLSafeTimedSerializer(secret, salt="repse.file-token")
        self._ttl = settings.download_token_ttl_seconds
        self._root.mkdir(parents=True, exist_ok=True, mode=0o700)

    def _abs_path(self, relative: str) -> Path:
        # Defense in depth: refuse anything that tries to escape the root.
        candidate = (self._root / relative).resolve()
        if not str(candidate).startswith(str(self._root.resolve())):
            raise ValueError("Path traversal detected")
        return candidate

    def save(
        self,
        *,
        organization_id: int,
        supplier_id: int,
        document_id: int,
        version: int,
        extension: str,
        stream: BinaryIO,
    ) -> StoredFile:
        ext = extension.lstrip(".").lower()
        rel = f"{organization_id}/{supplier_id}/{document_id}/v{version}.{ext}"
        path = self._abs_path(rel)
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)

        sha = hashlib.sha256()
        size = 0
        with open(path, "wb") as out:
            while chunk := stream.read(1 << 16):
                out.write(chunk)
                sha.update(chunk)
                size += len(chunk)
        os.chmod(path, 0o640)
        return StoredFile(relative_path=rel, size_bytes=size, sha256_hex=sha.hexdigest())

    def open(self, relative_path: str) -> BinaryIO:
        return open(self._abs_path(relative_path), "rb")

    def issue_download_token(
        self, *, file_id: int, user_id: int, organization_id: int
    ) -> str:
        return self._serializer.dumps(
            {"file_id": file_id, "user_id": user_id, "organization_id": organization_id}
        )

    def verify_download_token(self, token: str) -> dict[str, int]:
        try:
            payload = self._serializer.loads(token, max_age=self._ttl)
        except SignatureExpired as exc:
            raise TokenExpired("Token expired") from exc
        except BadSignature as exc:
            raise InvalidToken("Token signature invalid") from exc
        if not isinstance(payload, dict):
            raise InvalidToken("Token payload malformed")
        return payload  # type: ignore[return-value]


class InvalidToken(Exception):
    pass


class TokenExpired(Exception):
    pass

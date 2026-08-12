"""Unit tests para FileStore: unicidad de rutas UUID4 y retrocompatibilidad."""
from __future__ import annotations

import uuid
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from repse.documents.storage import FileStore


def _make_settings(upload_root: Path) -> MagicMock:
    s = MagicMock()
    s.upload_root = upload_root
    s.download_token_ttl_seconds = 300
    return s


_CONTENT = b"contenido de prueba para almacenamiento"
_SAVE_KWARGS = dict(organization_id=1, supplier_id=2, document_id=3, version=1, extension="pdf")


# T002 [US1] — dos saves con mismos parámetros deben producir rutas distintas
def test_two_saves_produce_distinct_paths(tmp_path: Path) -> None:
    store = FileStore(_make_settings(tmp_path))
    s1 = store.save(**_SAVE_KWARGS, stream=BytesIO(_CONTENT))
    s2 = store.save(**_SAVE_KWARGS, stream=BytesIO(_CONTENT))
    assert s1.relative_path != s2.relative_path


# T003 [US1] — la ruta generada contiene un UUID4 válido entre versión y extensión
def test_saved_path_contains_valid_uuid4(tmp_path: Path) -> None:
    store = FileStore(_make_settings(tmp_path))
    stored = store.save(**_SAVE_KWARGS, stream=BytesIO(_CONTENT))
    # Formato esperado del nombre: "v1.<uuid4>.pdf"
    # UUID4 usa guiones, no puntos → split(".") da exactamente ["v1", "<uuid>", "pdf"]
    filename = Path(stored.relative_path).name
    parts = filename.split(".")
    assert len(parts) == 3, f"Formato inesperado: {filename!r}"
    uuid_segment = parts[1]
    parsed = uuid.UUID(uuid_segment, version=4)
    assert parsed.version == 4


# T006 [US2] — el archivo guardado se puede leer y su contenido es íntegro
def test_open_returns_saved_content(tmp_path: Path) -> None:
    store = FileStore(_make_settings(tmp_path))
    stored = store.save(**_SAVE_KWARGS, stream=BytesIO(_CONTENT))
    with store.open(stored.relative_path) as fh:
        assert fh.read() == _CONTENT


# T007 [US3] — delete elimina el archivo físico
def test_delete_removes_file(tmp_path: Path) -> None:
    store = FileStore(_make_settings(tmp_path))
    stored = store.save(**_SAVE_KWARGS, stream=BytesIO(_CONTENT))
    abs_path = tmp_path / stored.relative_path
    assert abs_path.exists()
    store.delete(stored.relative_path)
    assert not abs_path.exists()


# T008 [US3] — archivos con ruta antigua (sin UUID) siguen siendo legibles
def test_legacy_path_readable(tmp_path: Path) -> None:
    store = FileStore(_make_settings(tmp_path))
    legacy_rel = "1/2/3/v1.pdf"
    legacy_abs = tmp_path / legacy_rel
    legacy_abs.parent.mkdir(parents=True, exist_ok=True)
    legacy_abs.write_bytes(_CONTENT)
    with store.open(legacy_rel) as fh:
        assert fh.read() == _CONTENT

"""Stubs de dependencias externas pesadas para tests unitarios.

Permite importar módulos del backend que dependen de pytesseract / pdf2image /
PIL / itsdangerous / etc. sin necesitar el entorno completo del proyecto.
Solo se aplica en la carpeta tests/unit/; los tests de integración usan el
entorno real (testcontainers).
"""
from __future__ import annotations

import importlib.util
import sys
import types
from types import SimpleNamespace


def _stub(name: str, **attrs) -> types.ModuleType:  # type: ignore[return]
    # Only stub modules that are NOT actually installed: pytest imports this
    # conftest while collecting the whole tests/ tree, and stubbing a real
    # package would poison the integration tests in the same run.
    try:
        if importlib.util.find_spec(name) is not None:
            return sys.modules.get(name, types.ModuleType(name))
    except (ImportError, ModuleNotFoundError, ValueError):
        pass
    m = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(m, k, v)
    sys.modules.setdefault(name, m)
    return m


# repse.documents.ocr — stubbear el módulo completo evita toda la cadena de
# dependencias externas (pytesseract → pdf2image → PIL → structlog → …).
_ocr_result = SimpleNamespace(raw_text=None, rfc=None, issued_at=None, valid_until=None)
_stub("repse.documents.ocr", run_ocr=lambda *a, **kw: _ocr_result)

# pdf2image
_pdf2image = _stub("pdf2image", convert_from_bytes=lambda *a, **kw: [])
# PIL / Pillow
_pil = _stub("PIL")
_stub("PIL.Image", new=lambda *a, **kw: None, open=lambda *a, **kw: None)
if "PIL.Image" in sys.modules:
    _pil.Image = sys.modules["PIL.Image"]
# pytesseract
_stub("pytesseract", image_to_string=lambda *a, **kw: "")
# itsdangerous
_bad_sig = type("BadSignature", (Exception,), {})
_sig_expired = type("SignatureExpired", (Exception,), {})

class _TimestampSigner:
    def __init__(self, *a, **kw): pass
    def sign(self, v): return v
    def unsign(self, v, **kw): return v

class _URLSafeTimedSerializer:
    def __init__(self, *a, **kw): pass
    def dumps(self, obj, **kw): return ""
    def loads(self, s, **kw): return {}

_stub(
    "itsdangerous",
    BadSignature=_bad_sig,
    SignatureExpired=_sig_expired,
    TimestampSigner=_TimestampSigner,
    URLSafeTimedSerializer=_URLSafeTimedSerializer,
)
# structlog
_stub("structlog", get_logger=lambda *a, **kw: SimpleNamespace(
    info=lambda *a, **kw: None,
    warning=lambda *a, **kw: None,
    error=lambda *a, **kw: None,
))
# sentry_sdk
_stub("sentry_sdk")
_stub("sentry_sdk.integrations")
_stub("sentry_sdk.integrations.fastapi")
# slowapi
_stub("slowapi")
_stub("slowapi.util")
_stub("slowapi.errors")
# prometheus_client
_stub("prometheus_client")
# passlib
_stub("passlib")
_stub("passlib.context", CryptContext=lambda **kw: SimpleNamespace(
    hash=lambda s: s, verify=lambda p, h: p == h
))

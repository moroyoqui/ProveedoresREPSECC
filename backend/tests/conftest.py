"""Shared pytest fixtures.

Spins up MySQL via testcontainers (or honors TEST_DB_URL), applies the Alembic
baseline + seed migrations, and exposes:

    * `engine`, `db_session` — bound to a rollback-only connection per test.
    * `client` — anonymous TestClient.
    * `client_with_session` + `session_user` — authenticated TestClient bound to
      a freshly provisioned Org with an admin user.
    * Cross-tenant fixtures for isolation tests.

Skip integration tests with `pytest -m "not integration"` if Docker isn't
available.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from dataclasses import dataclass

import pytest


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def mysql_url() -> Iterator[str]:
    url = os.getenv("TEST_DB_URL")
    if url:
        yield url
        return
    try:
        from testcontainers.mysql import MySqlContainer
    except ImportError:  # pragma: no cover
        pytest.skip("testcontainers not installed")
    with MySqlContainer("mysql:8.0", dialect="pymysql") as mysql:
        yield mysql.get_connection_url()


@pytest.fixture(scope="session")
def engine(mysql_url: str):
    from sqlalchemy import create_engine

    eng = create_engine(mysql_url, future=True)
    from alembic import command
    from alembic.config import Config

    cfg = Config("backend/alembic.ini")
    cfg.set_main_option("sqlalchemy.url", mysql_url)
    cfg.set_main_option("script_location", "backend/alembic")
    # alembic/env.py builds the URL from Settings (env vars), not from this
    # Config: mirror the testcontainer URL into the environment so the
    # migration runs against the test database.
    from sqlalchemy.engine import make_url

    parsed = make_url(mysql_url)
    os.environ.update(
        {
            "DB_HOST": parsed.host or "localhost",
            "DB_PORT": str(parsed.port or 3306),
            "DB_NAME": parsed.database or "test",
            "DB_USER": parsed.username or "test",
            "DB_PASS": parsed.password or "test",
        }
    )
    from repse import config as cfg_mod

    cfg_mod.get_settings.cache_clear()
    command.upgrade(cfg, "head")
    # Import the app eagerly so all routes capture the ORIGINAL get_settings
    # before any test fixture monkeypatches it; app fixtures then swap settings
    # via app.dependency_overrides keyed by that original function.
    import repse.main  # noqa: F401
    try:
        yield eng
    finally:
        eng.dispose()


@pytest.fixture()
def connection(engine) -> Iterator:  # type: ignore[no-untyped-def]
    """Single connection per test with an outer transaction rolled back at teardown.

    Both `db_session` and the app's SessionLocal bind to this connection using
    savepoints, so data committed by fixtures is visible to request handlers
    while the database stays clean between tests.
    """
    conn = engine.connect()
    trans = conn.begin()
    try:
        yield conn
    finally:
        if trans.is_active:
            trans.rollback()
        conn.close()


@pytest.fixture()
def db_session(connection) -> Iterator:  # type: ignore[no-untyped-def]
    from sqlalchemy.orm import Session

    session = Session(
        bind=connection,
        autoflush=False,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )
    try:
        yield session
    finally:
        session.close()


# ---------------------------------------------------------------------------
# FastAPI app + test client
# ---------------------------------------------------------------------------


@pytest.fixture()
def app(engine, connection, monkeypatch):  # type: ignore[no-untyped-def]
    """Imports and configures the FastAPI app for tests."""
    from repse import config as cfg_mod

    real_get_settings = cfg_mod.get_settings

    settings = cfg_mod.Settings(
        app_secret="x" * 32,  # type: ignore[arg-type]
        db_pass="x",  # type: ignore[arg-type]
        app_base_url="http://testserver",
        upload_root=os.path.abspath("./var/test-uploads"),  # type: ignore[arg-type]
    )
    if hasattr(cfg_mod.get_settings, "cache_clear"):
        cfg_mod.get_settings.cache_clear()
    monkeypatch.setattr(cfg_mod, "get_settings", lambda: settings)

    from repse.db import session as db_session_mod

    db_session_mod._engine = engine
    from sqlalchemy.orm import sessionmaker

    db_session_mod._SessionLocal = sessionmaker(
        bind=connection,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )

    from repse.main import app

    app.dependency_overrides[real_get_settings] = lambda: settings
    try:
        yield app
    finally:
        app.dependency_overrides.pop(real_get_settings, None)


@dataclass
class SessionUser:
    id: int
    email: str
    organization_id: int
    role: str


@pytest.fixture()
def client(app):  # type: ignore[no-untyped-def]
    from fastapi.testclient import TestClient

    return TestClient(app)


@pytest.fixture()
def session_user(db_session, app) -> SessionUser:
    from repse.db.tenant_filter import with_admin_scope
    from repse.organizations.models import Organization
    from repse.supplier_types.provisioning import provision_organization
    from repse.users.models import Role, User, UserStatus

    with with_admin_scope():
        org = Organization(
            legal_name="Org Test",
            rfc="TST900101AAA",
            contact_email="admin@test.mx",
        )
        db_session.add(org)
        db_session.flush()
        user = User(
            organization_id=org.id,
            email="admin@test.mx",
            display_name="Admin Test",
            role=Role.ADMIN,
            status=UserStatus.ACTIVE,
        )
        db_session.add(user)
        db_session.flush()
        provision_organization(db_session, organization_id=org.id)
        db_session.commit()
    return SessionUser(
        id=user.id,
        email=user.email,
        organization_id=org.id,
        role=user.role.value,
    )


@pytest.fixture()
def client_with_session(app, session_user):  # type: ignore[no-untyped-def]
    from fastapi.testclient import TestClient
    from repse.auth.session import SessionManager, SessionPayload, fresh_expiry
    from repse.config import get_settings

    sm = SessionManager(get_settings())
    payload = SessionPayload(
        user_id=session_user.id,
        organization_id=session_user.organization_id,
        role=session_user.role,
        expires_at=fresh_expiry(),
    )
    token = sm._serializer.dumps(  # type: ignore[attr-defined]
        {
            "user_id": payload.user_id,
            "organization_id": payload.organization_id,
            "role": payload.role,
            "expires_at": payload.expires_at.isoformat(),
        }
    )
    c = TestClient(app)
    c.cookies.set("session", token)
    return c


@pytest.fixture()
def seeded_supplier(db_session, session_user):  # type: ignore[no-untyped-def]
    from sqlalchemy import select

    from repse.db.tenant_filter import set_current_tenant
    from repse.suppliers.models import Supplier, SupplierStatus
    from repse.supplier_types.models import SupplierType, SupplierTypeOrigin

    set_current_tenant(session_user.organization_id)
    st = db_session.execute(
        select(SupplierType).where(SupplierType.origin == SupplierTypeOrigin.SYSTEM)
    ).scalar_one()
    s = Supplier(
        organization_id=session_user.organization_id,
        supplier_type_id=st.id,
        legal_name="Servicios Industriales del Norte",
        rfc="SIN9001022Y3",
        contact_email="juanp@sin.mx",
        status=SupplierStatus.ACTIVE,
    )
    db_session.add(s)
    db_session.commit()
    db_session.refresh(s)
    return s


@pytest.fixture()
def opinion_sat_type(db_session):  # type: ignore[no-untyped-def]
    from sqlalchemy import select

    from repse.document_types.models import DocumentType

    return db_session.execute(
        select(DocumentType).where(DocumentType.slug == "opinion-sat")
    ).scalar_one()


# ---------------------------------------------------------------------------
# Cross-tenant fixtures for the isolation test
# ---------------------------------------------------------------------------


def _make_org_with_admin(db_session, *, suffix: str):  # type: ignore[no-untyped-def]
    from repse.db.tenant_filter import with_admin_scope
    from repse.organizations.models import Organization
    from repse.supplier_types.provisioning import provision_organization
    from repse.users.models import Role, User, UserStatus

    with with_admin_scope():
        org = Organization(
            legal_name=f"Org {suffix}",
            rfc=f"O{suffix}900101AAA"[:13],
            contact_email=f"admin-{suffix}@test.mx",
        )
        db_session.add(org)
        db_session.flush()
        user = User(
            organization_id=org.id,
            email=f"admin-{suffix}@test.mx",
            display_name=f"Admin {suffix}",
            role=Role.ADMIN,
            status=UserStatus.ACTIVE,
        )
        db_session.add(user)
        db_session.flush()
        provision_organization(db_session, organization_id=org.id)
        db_session.commit()
    return org, user


def _client_for(app, *, user_id: int, organization_id: int, role: str):  # type: ignore[no-untyped-def]
    from fastapi.testclient import TestClient

    from repse.auth.session import SessionManager, fresh_expiry
    from repse.config import get_settings

    sm = SessionManager(get_settings())
    token = sm._serializer.dumps(  # type: ignore[attr-defined]
        {
            "user_id": user_id,
            "organization_id": organization_id,
            "role": role,
            "expires_at": fresh_expiry().isoformat(),
        }
    )
    c = TestClient(app)
    c.cookies.set("session", token)
    return c


@pytest.fixture()
def client_with_session_org_a(app, db_session):  # type: ignore[no-untyped-def]
    org, user = _make_org_with_admin(db_session, suffix="A")
    return _client_for(app, user_id=user.id, organization_id=org.id, role="admin")


@pytest.fixture()
def client_with_session_org_b(app, db_session):  # type: ignore[no-untyped-def]
    org, user = _make_org_with_admin(db_session, suffix="B")
    return _client_for(app, user_id=user.id, organization_id=org.id, role="admin")


@pytest.fixture()
def supplier_in_org_a(db_session, client_with_session_org_a):  # type: ignore[no-untyped-def]
    from sqlalchemy import select

    from repse.db.tenant_filter import set_current_tenant, with_admin_scope
    from repse.organizations.models import Organization
    from repse.suppliers.models import Supplier, SupplierStatus
    from repse.supplier_types.models import SupplierType, SupplierTypeOrigin

    with with_admin_scope():
        org = db_session.execute(
            select(Organization).where(Organization.legal_name == "Org A")
        ).scalar_one()
        st = db_session.execute(
            select(SupplierType).where(
                SupplierType.organization_id == org.id,
                SupplierType.origin == SupplierTypeOrigin.SYSTEM,
            )
        ).scalar_one()
        set_current_tenant(org.id)
        s = Supplier(
            organization_id=org.id,
            supplier_type_id=st.id,
            legal_name="Proveedor de A",
            rfc="AAA900101AAA"[:13],
            status=SupplierStatus.ACTIVE,
        )
        db_session.add(s)
        db_session.commit()
        db_session.refresh(s)
    return s


@pytest.fixture()
def document_in_org_a(db_session, supplier_in_org_a, opinion_sat_type):  # type: ignore[no-untyped-def]
    from datetime import date

    from sqlalchemy import select

    from repse.db.tenant_filter import set_current_tenant, with_admin_scope
    from repse.documents.models import Document, DocumentStatus, OcrStatus
    from repse.users.models import User

    with with_admin_scope():
        set_current_tenant(supplier_in_org_a.organization_id)
        uploader_id = db_session.execute(
            select(User.id).where(User.organization_id == supplier_in_org_a.organization_id)
        ).scalars().first()
        doc = Document(
            organization_id=supplier_in_org_a.organization_id,
            supplier_id=supplier_in_org_a.id,
            document_type_id=opinion_sat_type.id,
            coverage_period_start=date(2026, 4, 1),
            coverage_period_end=date(2026, 4, 30),
            due_date_calculated=date(2026, 5, 31),
            due_date_effective=date(2026, 5, 31),
            status=DocumentStatus.VALID,
            file_path="dummy",
            file_name_original="dummy.pdf",
            file_size_bytes=4,
            file_mime_type="application/pdf",
            file_sha256="0" * 64,
            ocr_status=OcrStatus.NOT_RUN,
            uploaded_by=uploader_id,
        )
        db_session.add(doc)
        db_session.commit()
        db_session.refresh(doc)
    return doc

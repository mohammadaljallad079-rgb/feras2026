"""Shared pytest fixtures. Tests run against a real PostgreSQL database."""

from __future__ import annotations

import os
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://safir:safir@localhost:5432/safir_test")
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("STORAGE_DIR", "/tmp/safir-test-storage")

from app.core.db import Base, get_db  # noqa: E402
from app.core.security import hash_password  # noqa: E402
import app.models  # noqa: E402,F401  (must precede the FastAPI instance import)
from app.main import app  # noqa: E402
from app.models.identity import Role, RolePermission, User, UserCompany, UserRole  # noqa: E402
from app.api.v1.users import ensure_system_roles  # noqa: E402

TEST_URL = os.environ["DATABASE_URL"]


@pytest.fixture(scope="session")
def engine():
    eng = create_engine(TEST_URL, future=True)
    Base.metadata.drop_all(eng)
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)
    eng.dispose()


@pytest.fixture()
def db(engine) -> Iterator[Session]:
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = factory()
    # Each test starts from a clean database so uniqueness constraints and
    # isolation assertions are not affected by earlier tests.
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE " + ", ".join(_table_names(engine)) + " RESTART IDENTITY CASCADE"))
    ensure_system_roles(session)
    try:
        yield session
    finally:
        session.close()


def _table_names(engine) -> list[str]:
    from sqlalchemy import inspect

    return inspect(engine).get_table_names()


@pytest.fixture()
def client(db: Session) -> Iterator[TestClient]:
    def override() -> Iterator[Session]:
        yield db

    app.dependency_overrides[get_db] = override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def make_user(db: Session):
    counter = {"n": 0}

    def _make(email: str, roles: list[str], companies: list[int] | None = None, active: bool = True) -> User:
        user = db.query(User).filter(User.email == email).one_or_none()
        if user is None:
            user = User(
                email=email,
                full_name_ar=email,
                full_name_en=email,
                locale="ar",
                password_hash=hash_password("Passw0rd!"),
                is_active=active,
            )
            db.add(user)
            db.flush()
        for slug in roles:
            role = db.query(Role).filter(Role.slug == slug).one()
            exists = db.query(UserRole).filter(UserRole.user_id == user.id, UserRole.role_id == role.id).one_or_none()
            if exists is None:
                db.add(UserRole(user_id=user.id, role_id=role.id))
        for cid in companies or []:
            if db.query(UserCompany).filter(UserCompany.user_id == user.id, UserCompany.company_id == cid).one_or_none() is None:
                db.add(UserCompany(user_id=user.id, company_id=cid))
        db.commit()
        counter["n"] += 1
        return user

    return _make


@pytest.fixture()
def login(client: TestClient):
    def _login(email: str) -> dict[str, str]:
        resp = client.post("/api/v1/auth/login", json={"email": email, "password": "Passw0rd!"})
        assert resp.status_code == 200, resp.text
        return {"Authorization": f"Bearer {resp.json()['access_token']}"}

    return _login

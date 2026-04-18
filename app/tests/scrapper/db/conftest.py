import os
import pathlib
import subprocess
from collections.abc import Generator
from typing import Any

import psycopg
import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from src.scrapper.db.engine import create_engine, create_session_factory
from src.scrapper.repository.orm_repository import OrmLinkRepository
from src.scrapper.repository.sql_repository import SqlLinkRepository
from src.scrapper.settings import AccessType, ScrapperSettings

_SCHEMA_FILES = [
    pathlib.Path(__file__).parent.parent.parent.parent / "migrations" / "00-initial-schema.sql",
    pathlib.Path(__file__).parent.parent.parent.parent / "migrations" / "01-identity-schema.sql",
]

_PODMAN_BIN = "/opt/podman/bin/podman"


def _resolve_docker_host() -> str | None:
    if host := os.environ.get("DOCKER_HOST"):
        return host
    try:
        result = subprocess.run(
            [
                _PODMAN_BIN,
                "machine",
                "inspect",
                "--format",
                "{{.ConnectionInfo.PodmanSocket.Path}}",
            ],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            return f"unix://{result.stdout.strip()}"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None


def _docker_available() -> bool:
    docker_host = _resolve_docker_host()
    if docker_host:
        os.environ["DOCKER_HOST"] = docker_host
        os.environ.setdefault("TESTCONTAINERS_RYUK_DISABLED", "true")
    try:
        import docker

        client = docker.from_env()
        client.ping()
    except Exception:  # noqa: BLE001
        return False
    else:
        return True


_NO_DOCKER = not _docker_available()


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    skip = pytest.mark.skip(reason="Docker/Podman is not available")
    for item in items:
        if "scrapper/db" in str(item.fspath) and _NO_DOCKER:
            item.add_marker(skip)


@pytest.fixture(scope="session")
def pg_container() -> Generator[Any, None, None]:
    from testcontainers.postgres import PostgresContainer

    with PostgresContainer("postgres:16", driver=None) as pg:
        yield pg


@pytest.fixture(scope="session")
def pg_dsn(pg_container: Any) -> str:
    raw = pg_container.get_connection_url()
    for driver in ("+psycopg2", "+pg8000", "+psycopg", "+asyncpg"):
        raw = raw.replace(driver, "")
    return str(raw)


@pytest.fixture(scope="session")
def pg_psycopg_url(pg_dsn: str) -> str:
    return pg_dsn.replace("postgresql://", "postgresql+psycopg://", 1)


def _extract_sql_statements(sql: str) -> list[str]:
    statements = []
    for block in sql.split(";"):
        lines = [ln for ln in block.splitlines() if not ln.strip().startswith("--")]
        stmt = "\n".join(lines).strip()
        if stmt:
            statements.append(stmt)
    return statements


@pytest.fixture(scope="session", autouse=True)
def apply_schema(pg_dsn: str) -> None:
    if _NO_DOCKER:
        return
    with psycopg.connect(pg_dsn) as conn:
        for schema_file in _SCHEMA_FILES:
            for stmt in _extract_sql_statements(schema_file.read_text()):
                conn.execute(stmt)
        conn.commit()


@pytest.fixture(scope="session")
def db_engine(pg_psycopg_url: str) -> AsyncEngine:
    return create_engine(pg_psycopg_url)


@pytest.fixture(scope="session")
def session_factory(db_engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return create_session_factory(db_engine)


@pytest.fixture
def orm_repository(session_factory: async_sessionmaker[AsyncSession]) -> OrmLinkRepository:
    return OrmLinkRepository(session_factory)


@pytest.fixture
def sql_repository(pg_dsn: str) -> SqlLinkRepository:
    return SqlLinkRepository(pg_dsn)


@pytest.fixture
def settings_orm(pg_psycopg_url: str) -> ScrapperSettings:
    return ScrapperSettings(  # type: ignore[call-arg]
        db_url=pg_psycopg_url,
        access_type=AccessType.ORM,
    )


@pytest.fixture
def settings_sql(pg_psycopg_url: str) -> ScrapperSettings:
    return ScrapperSettings(  # type: ignore[call-arg]
        db_url=pg_psycopg_url,
        access_type=AccessType.SQL,
    )

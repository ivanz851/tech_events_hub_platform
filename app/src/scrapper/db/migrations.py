import subprocess
from pathlib import Path

__all__ = ("run_liquibase_migrations",)

_MIGRATIONS_DIR = Path(__file__).parent.parent.parent.parent / "migrations"


def run_liquibase_migrations(db_url: str) -> None:
    jdbc_url = _to_jdbc_url(db_url)
    subprocess.run(  # noqa: S603
        [  # noqa: S607
            "liquibase",
            f"--searchPath={_MIGRATIONS_DIR}",
            "--changelog-file=master.xml",
            f"--url={jdbc_url}",
            "update",
        ],
        check=True,
    )


def _to_jdbc_url(db_url: str) -> str:
    for prefix in ("postgresql+psycopg://", "postgresql+asyncpg://", "postgresql://"):
        if db_url.startswith(prefix):
            return db_url.replace(prefix, "jdbc:postgresql://", 1)
    return db_url

import pytest

_DOCKER_MISSING = False

try:
    import docker

    docker.from_env().ping()
except Exception:  # noqa: BLE001
    _DOCKER_MISSING = True

skip_without_docker = pytest.mark.skipif(
    _DOCKER_MISSING,
    reason="Docker not available",
)

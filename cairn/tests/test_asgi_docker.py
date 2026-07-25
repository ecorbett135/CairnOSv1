# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0

from pathlib import Path


def test_asgi_dockerfile_uses_narrow_api_requirements():
    dockerfile = Path("Dockerfile.asgi").read_text(encoding="utf-8")

    assert "ARG RELEASE_PLATFORM=linux/arm64" in dockerfile
    assert (
        "FROM --platform=${RELEASE_PLATFORM} "
        "python:3.11.15-alpine3.23@sha256:"
        "f73754c398b259dfbbe482361dca8b464dea57da74efe5214966ca2ee767ee12"
        in dockerfile
    )
    assert "apk del .python-rundeps" in dockerfile
    assert "so:libsqlite3.so.0" not in dockerfile
    assert "requirements.api.txt" in dockerfile
    assert "requirements.txt" not in dockerfile
    assert "--upgrade pip" not in dockerfile
    assert "pip uninstall --yes setuptools wheel" in dockerfile
    assert "cairn.api.asgi_app:app" in dockerfile
    assert "--host" in dockerfile
    assert "0.0.0.0" in dockerfile
    assert "--port" in dockerfile
    assert "8010" in dockerfile


def test_asgi_requirements_are_container_scoped():
    requirements = Path("requirements.api.txt").read_text(encoding="utf-8")
    runtime_requirements = {
        line
        for line in requirements.splitlines()
        if line and not line.startswith("#")
    }

    assert runtime_requirements == {
        "fastapi==0.139.2",
        "starlette==1.3.1",
        "uvicorn==0.51.0",
    }
    assert "geopandas" not in requirements
    assert "rasterio" not in requirements
    assert "streamlit" not in requirements


def test_compose_exposes_local_cairnos_api_service():
    compose = Path("compose.yaml").read_text(encoding="utf-8")

    assert "cairnos-api:" in compose
    assert "platform: linux/arm64" in compose
    assert "Dockerfile.asgi" in compose
    assert "RELEASE_PLATFORM: linux/arm64" in compose
    assert '"8010:8010"' in compose
    assert "CAIRNOS_API_MAX_BODY_BYTES" in compose
    assert "CAIRNOS_BUILD_SHA" in compose
    assert "http://127.0.0.1:8010/health" in compose


def test_plan_api_docs_include_docker_desktop_run_command():
    docs = Path("docs/PLAN_API.md").read_text(encoding="utf-8")

    assert "docker compose up --build cairnos-api" in docs
    assert "http://127.0.0.1:8010/health" in docs
    assert "http://127.0.0.1:8010/v1/plan-options" in docs

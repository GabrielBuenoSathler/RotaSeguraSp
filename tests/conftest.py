"""Allow schema imports without requiring a configured database or local .env."""

import os

import pytest

for key, value in {
    "POSTGRES_USER": "test",
    "POSTGRES_PASSWORD": "test",
    "POSTGRES_HOST": "localhost",
    "POSTGRES_PORT": "5432",
}.items():
    os.environ.setdefault(key, value)


@pytest.fixture(autouse=True)
def deterministic_settings(monkeypatch):
    from app.core.config import settings

    for key, value in {
        "risk_radius_meters": 50,
        "risk_window_days": 365,
        "occurrence_date_column": None,
        "occurrence_group_date_column": None,
        "dataset_source": "Base de ocorrências importada pelo administrador",
        "dataset_updated_at": None,
        "route_alternates": 2,
        "nominatim_url": None,
    }.items():
        monkeypatch.setattr(settings, key, value)

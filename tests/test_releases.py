import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import release

REGISTRY = "ghcr.io/example/rotas"


def manifest(number):
    return {
        "version": str(number) * 40,
        "backend": f"{REGISTRY}/backend@sha256:{str(number) * 64}",
        "frontend": f"{REGISTRY}/frontend@sha256:{str(number) * 64}",
    }


class Docker:
    def __init__(self):
        self.calls = []
        self.failures = set()
        self.incompatible = set()
        self.wrong_label = False

    def __call__(self, command, *, env=None, **kwargs):
        self.calls.append((command, env))
        if command[:3] == ["docker", "image", "inspect"]:
            image = command[-1]
            repository, _, version = image.partition(":sha-")
            if not version:
                return "[]"
            return json.dumps(
                [
                    {
                        "Config": {
                            "Labels": {
                                "org.opencontainers.image.revision": "wrong"
                                if self.wrong_label
                                else version
                            }
                        },
                        "RepoDigests": [f"{repository}@sha256:{version[0] * 64}"],
                    }
                ]
            )
        if env:
            image = env["BACKEND_IMAGE"]
            if "-c" in command and command[-1] == release.SCHEMA_CHECK:
                return json.dumps(
                    {
                        "database": ["schema1"],
                        "image": [
                            "schema2" if image in self.incompatible else "schema1"
                        ],
                    }
                )
            if "up" in command and "backend" in command and image in self.failures:
                raise release.ReleaseError("healthcheck falhou")
        return ""

    def activations(self):
        return [
            (args, env["BACKEND_IMAGE"])
            for args, env in self.calls
            if "up" in args and "backend" in args
        ]


@pytest.fixture
def releases(tmp_path, monkeypatch):
    manager = release.Releases("prod", tmp_path)
    manager.state_file.parent.mkdir()
    docker = Docker()
    monkeypatch.setattr(release, "run", docker)
    return manager, docker


def test_deploy_and_rollback_keep_exact_images_without_migrations(releases):
    manager, docker = releases
    manager.deploy(REGISTRY, "1" * 40)
    manager.deploy(REGISTRY, "2" * 40)
    assert manager.state()["previous"] == manifest(1)
    docker.calls.clear()
    manager.rollback()
    assert manager.state() == {
        "current": manifest(1),
        "previous": manifest(2),
        "pending": None,
    }
    assert docker.activations()[0][1] == manifest(1)["backend"]
    args = docker.activations()[0][0]
    assert "--no-build" in args and "--no-deps" in args and "--wait" in args
    assert "--force-recreate" in args
    assert not any(
        "downgrade" in args or "upgrade" in args or "--build" in args
        for args, _ in docker.calls
    )


def test_failed_deploy_restores_current_and_preserves_previous(releases):
    manager, docker = releases
    manager.save({"current": manifest(2), "previous": manifest(1), "pending": None})
    docker.failures.add(manifest(3)["backend"])
    with pytest.raises(release.ReleaseError, match="anterior foi restaurada"):
        manager.deploy(REGISTRY, "3" * 40)
    assert manager.state() == {
        "current": manifest(2),
        "previous": manifest(1),
        "pending": None,
    }
    assert [image for _, image in docker.activations()] == [
        manifest(3)["backend"],
        manifest(2)["backend"],
    ]


def test_incompatible_rollback_does_not_touch_running_application(releases):
    manager, docker = releases
    state = {"current": manifest(2), "previous": manifest(1), "pending": None}
    manager.save(state)
    docker.incompatible.add(manifest(1)["backend"])
    with pytest.raises(release.ReleaseError, match="Esquema incompatível"):
        manager.rollback()
    assert manager.state() == state
    assert docker.activations() == []


def test_interrupted_release_recovers_last_healthy_version(releases):
    manager, docker = releases
    manager.save(
        {"current": manifest(2), "previous": manifest(1), "pending": manifest(3)}
    )
    with pytest.raises(release.ReleaseError, match="interrompido"):
        manager.deploy(REGISTRY, "4" * 40)
    manager.rollback()
    assert manager.state() == {
        "current": manifest(2),
        "previous": manifest(1),
        "pending": None,
    }
    assert docker.activations()[0][1] == manifest(2)["backend"]


def test_failed_recovery_keeps_pending_state_for_operator(releases):
    manager, docker = releases
    manager.save({"current": manifest(1), "previous": None, "pending": None})
    docker.failures.update([manifest(1)["backend"], manifest(2)["backend"]])
    with pytest.raises(release.ReleaseError, match="restauração também falhou"):
        manager.deploy(REGISTRY, "2" * 40)
    assert manager.state()["pending"] == manifest(2)
    assert manager.state()["current"] == manifest(1)


def test_first_failed_deploy_can_be_retried(releases):
    manager, docker = releases
    docker.failures.add(manifest(1)["backend"])
    with pytest.raises(release.ReleaseError, match="Primeiro deploy"):
        manager.deploy(REGISTRY, "1" * 40)
    assert manager.state()["pending"] == manifest(1)
    docker.failures.clear()
    manager.deploy(REGISTRY, "1" * 40)
    assert manager.state()["current"] == manifest(1)
    assert manager.state()["pending"] is None


def test_wrong_revision_is_rejected_before_changing_services(releases):
    manager, docker = releases
    docker.wrong_label = True
    with pytest.raises(release.ReleaseError, match="commit solicitado"):
        manager.deploy(REGISTRY, "1" * 40)
    assert docker.activations() == []
    assert not manager.state_file.exists()


def test_redeploy_same_version_keeps_rollback_target(releases):
    manager, _ = releases
    state = {"current": manifest(2), "previous": manifest(1), "pending": None}
    manager.save(state)
    manager.deploy(REGISTRY, "2" * 40)
    assert manager.state() == state


def test_ci_measurement_preserves_failed_exit_status(tmp_path, monkeypatch):
    summary = tmp_path / "summary.md"
    metrics = tmp_path / "metrics.jsonl"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    monkeypatch.setenv("CI_TIMINGS_FILE", str(metrics))
    script = Path(__file__).resolve().parents[1] / "scripts/ci_step.py"
    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "Failure",
            sys.executable,
            "-c",
            "raise SystemExit(7)",
        ],
        check=False,
    )
    assert result.returncode == 7
    record = json.loads(metrics.read_text())
    assert record["exit_code"] == 7
    assert record["seconds"] >= 0
    assert "Failure" in summary.read_text()

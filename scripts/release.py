#!/usr/bin/env python3
"""Deploy immutable application images; keep the database lifecycle explicit."""

import argparse
import fcntl
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_CHECK = """
import asyncio, json
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text
from app.core.database import engine

async def main():
    try:
        async with engine.connect() as connection:
            exists = await connection.scalar(text("SELECT to_regclass('public.alembic_version')"))
            current = list((await connection.execute(text("SELECT version_num FROM alembic_version"))).scalars()) if exists else []
        print(json.dumps({"database": sorted(current), "image": sorted(ScriptDirectory.from_config(Config("alembic.ini")).get_heads())}))
    finally:
        await engine.dispose()

asyncio.run(main())
"""


class ReleaseError(RuntimeError):
    pass


def run(command, *, env=None, capture=False, input=None):
    result = subprocess.run(
        command, env=env, input=input, text=True, capture_output=capture, check=False
    )
    if result.returncode:
        # Do not echo command arguments, environment files or captured DB errors.
        raise ReleaseError(f"Comando {command[0]} falhou (saída {result.returncode}).")
    return result.stdout or ""


class Releases:
    def __init__(self, environment, root=ROOT):
        self.root = root
        self.environment = environment
        self.env_file = root / "deploy" / f".env.{environment}"
        self.state_file = root / ".releases" / f"{environment}.json"

    def state(self):
        if self.state_file.exists():
            return json.loads(self.state_file.read_text())
        return {"current": None, "previous": None, "pending": None}

    def save(self, state):
        temporary = self.state_file.with_suffix(".tmp")
        with temporary.open("w") as output:
            json.dump(state, output, indent=2)
            output.flush()
            os.fsync(output.fileno())
        temporary.replace(self.state_file)

    def compose(self, release, *args, **kwargs):
        env = {
            **os.environ,
            "BACKEND_IMAGE": release["backend"],
            "FRONTEND_IMAGE": release["frontend"],
        }
        return run(
            [
                "docker",
                "compose",
                "--project-name",
                f"rotasegura-{self.environment}",
                "--env-file",
                str(self.env_file),
                "-f",
                str(self.root / "deploy/compose.yaml"),
                "-f",
                str(self.root / "deploy/compose.release.yaml"),
                *args,
            ],
            env=env,
            **kwargs,
        )

    def resolve(self, registry, version):
        if not re.fullmatch(r"[0-9a-f]{40}", version):
            raise ReleaseError(
                "Use o SHA completo do commit (40 caracteres minúsculos)."
            )
        if not re.fullmatch(r"[a-z0-9][a-z0-9./:_-]*", registry):
            raise ReleaseError(
                "Prefixo de imagens inválido; use o endereço em minúsculas."
            )
        release = {"version": version}
        for service in ("backend", "frontend"):
            repository = f"{registry.rstrip('/')}/{service}"
            tag = f"{repository}:sha-{version}"
            run(["docker", "pull", "--quiet", tag])
            info = json.loads(run(["docker", "image", "inspect", tag], capture=True))[0]
            if (info["Config"].get("Labels") or {}).get(
                "org.opencontainers.image.revision"
            ) != version:
                raise ReleaseError(
                    f"A imagem {service} não corresponde ao commit solicitado."
                )
            digest = next(
                (
                    item
                    for item in info.get("RepoDigests", [])
                    if item.startswith(repository + "@sha256:")
                ),
                None,
            )
            if not digest:
                raise ReleaseError(f"Digest de {service} não encontrado.")
            release[service] = digest
        return release

    def ensure_images(self, release):
        for service in ("backend", "frontend"):
            reference = release[service]
            if not re.fullmatch(
                r"[a-z0-9][a-z0-9./:_-]*@sha256:[0-9a-f]{64}", reference
            ):
                raise ReleaseError(
                    "Estado inválido: a imagem precisa de um digest SHA256."
                )
            try:
                run(["docker", "image", "inspect", reference], capture=True)
            except ReleaseError:
                run(["docker", "pull", "--quiet", reference])

    def check_schema(self, release):
        output = self.compose(
            release,
            "run",
            "--rm",
            "--no-deps",
            "-e",
            "SQL_ECHO=false",
            "migrate",
            "python",
            "-c",
            SCHEMA_CHECK,
            capture=True,
        )
        schema = json.loads(output)
        if not schema["image"] or schema["database"] != schema["image"]:
            raise ReleaseError(
                "Esquema incompatível com a imagem. Migrações são uma operação separada; "
                "rollback nunca executa downgrade."
            )

    def apply(self, release):
        # Nginx resolves the backend at startup; refresh it even for flag-only changes.
        self.compose(
            release,
            "up",
            "-d",
            "--no-build",
            "--pull",
            "never",
            "--no-deps",
            "--force-recreate",
            "--wait",
            "--wait-timeout",
            "120",
            "backend",
            "frontend",
        )

    def activate(self, release):
        state = self.state()
        self.ensure_images(release)
        self.check_schema(release)
        self.save({**state, "pending": release})
        try:
            self.apply(release)
        except (ReleaseError, KeyboardInterrupt) as exc:
            if state["current"]:
                try:
                    self.ensure_images(state["current"])
                    self.check_schema(state["current"])
                    self.apply(state["current"])
                except (ReleaseError, KeyboardInterrupt) as recovery:
                    raise ReleaseError(
                        "A versão falhou e a restauração também falhou. Estado pendente "
                        "preservado; confira os serviços e execute rollback."
                    ) from recovery
                self.save({**state, "pending": None})
                raise ReleaseError(
                    "A versão falhou; a versão anterior foi restaurada."
                ) from exc
            raise ReleaseError(
                "Primeiro deploy falhou, sem versão anterior registrada. "
                "Corrija a causa e repita deploy; estado pendente preservado."
            ) from exc
        previous = (
            state["previous"] if state["current"] == release else state["current"]
        )
        self.save({"current": release, "previous": previous, "pending": None})
        print(f"Versão ativa: {release['version']}")

    def deploy(self, registry, version):
        state = self.state()
        if state.get("pending") and state.get("current"):
            raise ReleaseError(
                "Há um deploy interrompido. Execute rollback antes de continuar."
            )
        self.activate(self.resolve(registry, version))

    def rollback(self):
        state = self.state()
        target = state["current"] if state.get("pending") else state["previous"]
        if not target:
            raise ReleaseError("Não existe versão anterior registrada para restaurar.")
        self.activate(target)

    def migrate(self, registry, version):
        if self.state().get("pending"):
            raise ReleaseError("Resolva o deploy pendente antes de executar migrações.")
        release = self.resolve(registry, version)
        self.compose(
            release, "up", "-d", "--build", "--wait", "--wait-timeout", "120", "db"
        )
        self.compose(release, "run", "--rm", "--no-deps", "migrate")
        self.compose(
            release,
            "exec",
            "-T",
            "db",
            "sh",
            "-s",
            input=(self.root / "scripts/provision-db.sh").read_text(),
        )
        self.check_schema(release)
        print(
            "Migrações e permissões aplicadas. Execute deploy para trocar a aplicação."
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("environment", choices=["homolog", "prod"])
    commands = parser.add_subparsers(dest="action", required=True)
    for action in ("deploy", "migrate"):
        command = commands.add_parser(action)
        command.add_argument(
            "--registry", required=True, help="Ex.: ghcr.io/usuario/repositorio"
        )
        command.add_argument(
            "--version", required=True, help="SHA completo do commit publicado"
        )
    commands.add_parser("rollback")
    commands.add_parser("status")
    args = parser.parse_args()
    os.umask(0o077)
    releases = Releases(args.environment)
    try:
        if not releases.env_file.exists():
            raise ReleaseError(
                f"Execute scripts/env.sh {args.environment} init primeiro."
            )
        releases.state_file.parent.mkdir(parents=True, exist_ok=True)
        with releases.state_file.with_suffix(".lock").open("a") as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise ReleaseError(
                    "Outra operação de release está em andamento."
                ) from exc
            if args.action == "status":
                print(json.dumps(releases.state(), indent=2))
            elif args.action == "rollback":
                releases.rollback()
            else:
                getattr(releases, args.action)(args.registry, args.version)
    except (ReleaseError, OSError, ValueError) as exc:
        print(f"Release não concluída: {exc}", file=sys.stderr)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()

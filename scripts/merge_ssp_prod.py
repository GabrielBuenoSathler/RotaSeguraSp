#!/usr/bin/env python3
"""Acrescenta à produção somente registros posteriores ao corte atual."""

import argparse
import json
import subprocess
from datetime import UTC, datetime

from ingest_ssp import COLUMNS, ROOT, connect, ingest
from psycopg import sql


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--date-column", required=True, choices=["data_registro", "data_ocorrencia_bo"]
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Grava em rotasegura_prod; sem esta opção apenas simula",
    )
    args = parser.parse_args()
    columns = sql.SQL(", ").join(map(sql.Identifier, COLUMNS))
    with connect("test") as source, connect("prod") as destination:
        with destination.transaction():
            destination.execute(
                "SELECT pg_advisory_xact_lock(hashtext('ssp_occurrences_ingestion'))"
            )
            cutoff = destination.execute(
                sql.SQL("SELECT max({}) FROM public.ocorrencias_stg").format(
                    sql.Identifier(args.date_column)
                )
            ).fetchone()[0]
            if cutoff is None:
                parser.error(
                    "Produção vazia ou sem datas: não foi possível definir o corte."
                )
            candidates = source.execute(
                sql.SQL(
                    "SELECT count(*) FROM public.ocorrencias_stg WHERE {} > %s"
                ).format(sql.Identifier(args.date_column)),
                (cutoff,),
            ).fetchone()[0]
            print(
                f"Destino: rotasegura_prod; coluna: {args.date_column}; corte exclusivo: {cutoff}; candidatas: {candidates}",
                flush=True,
            )
            if args.apply:
                directory = ROOT / "backups"
                directory.mkdir(exist_ok=True, mode=0o700)
                backup = (
                    directory
                    / f"ocorrencias_stg-prod-{datetime.now(UTC):%Y%m%dT%H%M%S%fZ}.dump"
                )
                with backup.open("xb") as output:
                    backup.chmod(0o600)
                    subprocess.run(
                        [
                            "docker",
                            "exec",
                            "rotasegura-prod-db-1",
                            "sh",
                            "-c",
                            'exec pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc --table=public.ocorrencias_stg --no-owner --no-acl',
                        ],
                        stdout=output,
                        check=True,
                    )
                print(f"Backup criado: {backup}", flush=True)
            with source.cursor(name="ssp_prod_merge") as cursor:
                cursor.itersize = 5000
                cursor.execute(
                    sql.SQL(
                        "SELECT {} FROM public.ocorrencias_stg WHERE {} > %s"
                    ).format(columns, sql.Identifier(args.date_column)),
                    (cutoff,),
                )
                report = ingest(destination, cursor, dry_run=not args.apply)
            report.update(
                coluna=args.date_column,
                corte_exclusivo=str(cutoff),
                destino="rotasegura_prod",
            )
        print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()

import os
from datetime import date
from uuid import uuid4

import pytest
from openpyxl import Workbook

from scripts.ingest_ssp import COLUMNS, connect, ingest, normalize, rows


def test_normalize_dates_numbers_and_missing_coordinates():
    assert normalize("data_registro", "31/01/2026") == date(2026, 1, 31)
    assert normalize("latitude", "-23,55") == -23.55
    assert normalize("bairro", "NULL") is None
    with pytest.raises(ValueError):
        normalize("latitude", 91)
    with pytest.raises(ValueError):
        normalize("mes_estatistica", 13)
    with pytest.raises(ValueError):
        normalize("ano_bo", 2026.5)


def test_workbook_documentation_trailing_columns_and_filter(tmp_path):
    workbook = Workbook()
    workbook.active.append(["Documentação"])
    sheet = workbook.create_sheet("JAN-JUN_2026")
    sheet.append(
        [name.upper().replace("COD_IBGE", "COD IBGE") for name in COLUMNS] + [None]
    )
    row = [None] * len(COLUMNS)
    row[COLUMNS.index("num_bo")] = "TEST"
    row[COLUMNS.index("cod_ibge")] = 3550308
    row[COLUMNS.index("latitude")] = 12345
    row[COLUMNS.index("longitude")] = -46.63
    sheet.append(row)
    path = tmp_path / "data.xlsx"
    workbook.save(path)
    result = list(rows(path, municipality=3550308, limit=1))
    assert len(result) == 1
    assert result[0][COLUMNS.index("latitude")] is None
    assert result[0][COLUMNS.index("longitude")] is None
    assert list(rows(path, municipality=3509502)) == []


@pytest.mark.skipif(
    os.getenv("SSP_TEST_DATABASE") != "1",
    reason="Requer o PostgreSQL isolado de testes",
)
def test_real_insertion_deduplication_geometry_and_dry_run():
    record = dict.fromkeys(COLUMNS)
    record.update(
        num_bo=f"TEST-{uuid4()}",
        ano_bo=2026,
        rubrica="Teste de ingestão",
        latitude=-23.55,
        longitude=-46.63,
        bairro="SÉ",
    )
    first = tuple(record[column] for column in COLUMNS)
    missing = dict(record, num_bo=f"TEST-{uuid4()}", latitude=0, longitude=0)
    second = tuple(missing[column] for column in COLUMNS)
    with connect("test") as connection:
        with connection.transaction(force_rollback=True):
            assert ingest(connection, [first, second], dry_run=True)["inseridas"] == 0
            assert ingest(connection, [first, first, second])["inseridas"] == 2
            assert ingest(connection, [first, second])["inseridas"] == 0
            result = connection.execute(
                "SELECT ST_SRID(geom), ST_X(geom), ST_Y(geom), geog IS NOT NULL, bairro_normalizado FROM ocorrencias_stg WHERE num_bo=%s",
                (record["num_bo"],),
            ).fetchone()
            assert result == (4326, -46.63, -23.55, True, "se")
            assert connection.execute(
                "SELECT geom IS NULL AND geog IS NULL FROM ocorrencias_stg WHERE num_bo=%s",
                (missing["num_bo"],),
            ).fetchone()[0]
            with pytest.raises(ValueError):

                def broken():
                    yield first
                    raise ValueError("Arquivo inválido")

                ingest(connection, broken())
            assert ingest(connection, [first])["inseridas"] == 0

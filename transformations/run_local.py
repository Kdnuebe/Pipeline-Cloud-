"""
Exécute les transformations SQL EN LOCAL avec DuckDB (gratuit, joue le rôle d'Athena).

- Lit les Parquet bronze (dossier ./data/bronze)
- Construit la table silver puis les datamarts gold
- Écrit chaque couche en Parquet sous ./data/silver et ./data/gold

Le MÊME SQL (transformations/sql/*.sql) est rejoué sur AWS par Athena, via le job
Glue cloud / Step Functions (seul le jeton __DOW__ diffère entre moteurs).
"""
from __future__ import annotations

import os
import sys

import duckdb

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pipeline_common import DATA_ROOT, log, put_metric  # noqa: E402

SQL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sql")

# Remplacement du jeton __DOW__ (jour de semaine ISO 1=Lun..7=Dim) pour DuckDB
DUCKDB_DOW = "CAST(EXTRACT(isodow FROM t.tpep_pickup_datetime) AS INTEGER)"


def read_sql(name: str) -> str:
    with open(os.path.join(SQL_DIR, name), "r", encoding="utf-8") as f:
        return f.read().replace("__DOW__", DUCKDB_DOW)


def main() -> None:
    log("=== TRANSFORMATIONS SILVER/GOLD (DuckDB local) ===")
    con = duckdb.connect()

    # --- Sources bronze exposées comme des vues -----------------------------
    con.execute(
        f"""
        CREATE VIEW bronze_trips AS
            SELECT * FROM read_parquet('{DATA_ROOT}/bronze/trips/**/*.parquet',
                                       hive_partitioning = true, union_by_name = true);
        CREATE VIEW bronze_zones AS
            SELECT * FROM read_parquet('{DATA_ROOT}/bronze/zones/zones.parquet');
        CREATE VIEW bronze_weather AS
            SELECT * FROM read_parquet('{DATA_ROOT}/bronze/weather/**/*.parquet',
                                       hive_partitioning = true, union_by_name = true);
        """
    )

    # --- SILVER -------------------------------------------------------------
    con.execute(f"CREATE OR REPLACE TABLE silver_trips AS ({read_sql('silver_trips.sql')})")
    n_silver = con.execute("SELECT COUNT(*) FROM silver_trips").fetchone()[0]
    os.makedirs(f"{DATA_ROOT}/silver/trips", exist_ok=True)
    con.execute(
        f"COPY silver_trips TO '{DATA_ROOT}/silver/trips/silver.parquet' (FORMAT PARQUET)"
    )
    log(f"[silver] {n_silver:,} lignes -> {DATA_ROOT}/silver/trips/")
    put_metric("RowsProcessed", n_silver, dims={"layer": "silver"})

    # --- GOLD ---------------------------------------------------------------
    gold_models = {
        "demand_by_zone_hour": "gold_demand_by_zone_hour.sql",
        "tips_analysis": "gold_tips_analysis.sql",
    }
    for table, sql_file in gold_models.items():
        con.execute(f"CREATE OR REPLACE TABLE {table} AS ({read_sql(sql_file)})")
        n = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        os.makedirs(f"{DATA_ROOT}/gold/{table}", exist_ok=True)
        con.execute(
            f"COPY {table} TO '{DATA_ROOT}/gold/{table}/{table}.parquet' (FORMAT PARQUET)"
        )
        log(f"[gold]   {table}: {n:,} lignes -> {DATA_ROOT}/gold/{table}/")
        put_metric("RowsProcessed", n, dims={"layer": "gold", "table": table})

    con.close()
    log("=== TRANSFORMATIONS terminées ===")


if __name__ == "__main__":
    main()

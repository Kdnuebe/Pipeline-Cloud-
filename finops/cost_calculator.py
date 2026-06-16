"""
CALCULATEUR FINOPS — version SIMPLE (S3 + Athena uniquement).

Le traitement lourd se fait en LOCAL (gratuit). Sur le cloud, on ne paie que :
  - le stockage S3 (quelques centimes),
  - les requêtes Athena (5 $ par To de données scannées -> ici quelques Mo).
Pas de Glue, pas de Step Functions, pas de Lambda dans la version simple.

Lancer :  python finops/cost_calculator.py
"""
from __future__ import annotations

import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass

# --- Tarifs unitaires (USD, eu-west-3, ordres de grandeur 2024) -------------
PRICES = {
    "s3_gb_month": 0.023,        # stockage S3 Standard
    "athena_tb_scanned": 5.0,    # Athena : 5 $ par To scanné
    "s3_put_per_1k": 0.005,      # requêtes PUT (upload)
}

# --- Hypothèses du projet ---------------------------------------------------
ASSUMPTIONS = {
    "storage_gb": 0.3,             # bronze + silver + gold pour 1 mois
    "gb_scanned_per_build": 0.12,  # données lues par Athena pour reconstruire silver+gold
    "builds_dev": 20,              # nb de reconstructions pendant le dev/recette
    "builds_per_month": 8,         # reconstructions/mois en exploitation
    "explore_queries_month": 100,  # requêtes d'exploration (petites)
    "gb_per_explore": 0.01,
    "uploads": 200,                # nb d'objets uploadés (PUT)
}


def athena_cost(gb_scanned: float) -> float:
    return gb_scanned / 1024 * PRICES["athena_tb_scanned"]


def table(title: str, rows: list[tuple[str, float]]) -> float:
    print(f"### {title}\n")
    print("| Poste | Coût (USD) |")
    print("|---|---|")
    total = 0.0
    for label, cost in rows:
        print(f"| {label} | {cost:.4f} |")
        total += cost
    print(f"| **TOTAL** | **{total:.4f}** |\n")
    return total


def main() -> None:
    a = ASSUMPTIONS
    # ----- DEV / RECETTE -----
    dev_rows = [
        ("Stockage S3 (0,3 Go, 1 mois)", a["storage_gb"] * PRICES["s3_gb_month"]),
        ("Athena — reconstructions (20 × 0,12 Go)", athena_cost(a["builds_dev"] * a["gb_scanned_per_build"])),
        ("Athena — requêtes d'exploration", athena_cost(a["explore_queries_month"] * a["gb_per_explore"])),
        ("S3 — uploads (PUT)", a["uploads"] / 1000 * PRICES["s3_put_per_1k"]),
    ]
    table("Facturation DÉVELOPPEMENT & RECETTE", dev_rows)

    # ----- RUN MENSUEL -----
    run_rows = [
        ("Stockage S3", a["storage_gb"] * PRICES["s3_gb_month"]),
        ("Athena — reconstructions (8/mois)", athena_cost(a["builds_per_month"] * a["gb_scanned_per_build"])),
        ("Athena — exploration (100 requêtes)", athena_cost(a["explore_queries_month"] * a["gb_per_explore"])),
    ]
    monthly = table("Facturation EXPLOITATION (run mensuel)", run_rows)
    print(f"**Extrapolation : ~{monthly:.3f} USD/mois → ~{monthly*12:.2f} USD/an.**\n")
    print("*Optimisations : Parquet + partitionnement (moins de Go scannés par Athena), "
          "lifecycle S3 (Standard → IA → Glacier), traitement lourd en local (gratuit), "
          "suppression du bucket après la démo.*")
    print("\n*Comparaison : la version « industrialisée » (Glue + Step Functions, voir "
          "avance_optionnel/) coûterait ~3-4 USD/mois — la version simple est encore moins chère.*")


if __name__ == "__main__":
    main()

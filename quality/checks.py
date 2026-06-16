"""
COUCHE QUALITÉ — Tests de qualité automatisés (portables local + AWS).

Exécutés comme une tâche DÉDIÉE de la pipeline (entre silver et ML).
Si un test CRITIQUE échoue, le script sort en erreur -> l'orchestrateur déclenche
une alerte (SNS en cloud). Les résultats sont aussi publiés en métriques.

Une suite Great Expectations "vitrine" est fournie en plus (voir
quality/great_expectations_suite.py) pour le rapport, mais ce module-ci est
le filet de sécurité réellement branché dans l'orchestration.
"""
from __future__ import annotations

import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pipeline_common import DATA_ROOT, log, put_metric, read_parquet_dataset  # noqa: E402


def run_checks(df: pd.DataFrame) -> list[dict]:
    """Retourne la liste des tests avec leur statut. severity='critical' fait échouer."""
    results: list[dict] = []

    def check(name, passed, severity="critical", detail=""):
        results.append(
            {"name": name, "passed": bool(passed), "severity": severity, "detail": detail}
        )

    n = len(df)
    check("volume_non_vide", n > 0, detail=f"{n} lignes")

    # Complétude des colonnes clés
    for col in ["pickup_ts", "total_amount", "pu_location_id"]:
        nulls = int(df[col].isna().sum()) if col in df else n
        check(f"non_null__{col}", nulls == 0, detail=f"{nulls} nulls")

    # Bornes métier (cohérence)
    if "total_amount" in df:
        check("total_amount_positif", (df["total_amount"] >= 0).all())
    if "trip_duration_min" in df:
        ok = df["trip_duration_min"].between(1, 240).all()
        check("duree_plausible_1_240min", ok)
    if "tip_pct" in df:
        sub = df["tip_pct"].dropna()
        check("tip_pct_borne_0_100", sub.between(0, 100).mean() > 0.99,
              severity="warning", detail=f"{(sub.between(0,100).mean()*100):.2f}% dans [0,100]")

    # Intégrité référentielle (jointure zones réussie pour la majorité)
    if "pu_borough" in df:
        matched = df["pu_borough"].notna().mean()
        check("jointure_zones_ok", matched > 0.95, severity="warning",
              detail=f"{matched*100:.1f}% des courses ont un borough")

    # RGPD : la PII en clair ne doit JAMAIS atteindre la couche silver
    check("rgpd_pas_de_pii_claire", "driver_email" not in df.columns,
          detail="driver_email absent de silver" if "driver_email" not in df.columns
          else "FUITE: driver_email présent !")

    return results


def main() -> None:
    log("=== TESTS QUALITÉ (silver) ===")
    df = read_parquet_dataset(f"{DATA_ROOT}/silver/trips")
    results = run_checks(df)

    failed_critical = 0
    for r in results:
        status = "✅" if r["passed"] else ("⚠️" if r["severity"] == "warning" else "❌")
        log(f"  {status} {r['name']} {('— ' + r['detail']) if r['detail'] else ''}")
        if not r["passed"] and r["severity"] == "critical":
            failed_critical += 1

    put_metric("QualityFailedChecks", failed_critical)
    put_metric("QualityRowsTested", len(df))

    if failed_critical:
        log(f"=== QUALITÉ : {failed_critical} test(s) CRITIQUE(s) en échec -> ARRÊT ===")
        sys.exit(1)
    log("=== QUALITÉ : tous les tests critiques passent ===")


if __name__ == "__main__":
    main()

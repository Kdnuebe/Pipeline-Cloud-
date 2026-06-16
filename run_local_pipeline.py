"""
ORCHESTRATEUR LOCAL — exécute toute la pipeline de bout en bout, GRATUITEMENT.

C'est un orchestrateur SIMPLE mais complet (que tu maîtrises ligne par ligne) :
  - DÉPENDANCES : les étapes s'enchaînent dans l'ordre (chacune attend la précédente)
  - RETRY      : chaque étape est réessayée en cas d'échec transitoire
  - ALERTE     : en cas d'échec définitif, une alerte est émise (console + email SNS optionnel)
  - MONITORING : un rapport de run (durées, lignes traitées, statut) est affiché et sauvegardé

SCHEDULING (planification) — pour le lancer automatiquement chaque jour :
  - Windows : Planificateur de tâches -> action -> programme = le python.exe du .venv,
              arguments = run_local_pipeline.py 2024-01
  - Linux/macOS (cron) :  0 6 * * *  cd /chemin/projet && .venv/bin/python run_local_pipeline.py 2024-01

Usage :
    python run_local_pipeline.py                  # mois depuis .env
    python run_local_pipeline.py 2024-01 2024-02  # mois explicites
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass

DATA_ROOT = os.environ.get("DATA_ROOT", "./data").rstrip("/")
RETRIES = 2          # nb de nouvelles tentatives après un premier échec
RETRY_DELAY = 8      # secondes entre deux tentatives

STEPS = [
    ("BRONZE — Ingestion", [sys.executable, "data_ingestion/ingest.py"]),
    ("SILVER+GOLD — Transformations", [sys.executable, "transformations/run_local.py"]),
    ("QUALITÉ — Tests", [sys.executable, "quality/checks.py"]),
    ("ML — Entraînement & scoring", [sys.executable, "ml/train_score.py"]),
]


def run_step(label: str, cmd: list[str]) -> dict:
    """Exécute une étape avec retry. Retourne un dict de monitoring."""
    last_code = 0
    for attempt in range(1, RETRIES + 2):  # 1 essai initial + RETRIES
        t0 = time.time()
        res = subprocess.run(cmd)
        duration = round(time.time() - t0, 1)
        if res.returncode == 0:
            return {"etape": label, "statut": "OK", "tentatives": attempt, "duree_s": duration}
        last_code = res.returncode
        print(f"\n⚠️  '{label}' a échoué (tentative {attempt}/{RETRIES + 1}, code {res.returncode}).")
        if attempt <= RETRIES:
            print(f"    Nouvelle tentative dans {RETRY_DELAY}s…")
            time.sleep(RETRY_DELAY)
    return {"etape": label, "statut": "ÉCHEC", "tentatives": RETRIES + 1,
            "duree_s": duration, "code": last_code}


def alert_failure(label: str) -> None:
    """ALERTING : émet une alerte d'échec (console + email SNS si configuré dans .env)."""
    msg = f"[ALERTE] Pipeline NYC Taxi : échec définitif à l'étape '{label}'."
    print("\n" + "=" * 70 + f"\n❌ {msg}\n" + "=" * 70)
    topic = os.environ.get("ALERT_SNS_TOPIC_ARN")  # optionnel
    if topic:
        try:
            import boto3

            boto3.client("sns").publish(
                TopicArn=topic, Subject="[ALERTE] Pipeline NYC Taxi", Message=msg
            )
            print("📧 Alerte email envoyée via SNS.")
        except Exception as exc:  # ne pas faire échouer l'alerte elle-même
            print(f"   (Email SNS non envoyé : {exc})")


def count_rows(path: str) -> int | None:
    """MONITORING : compte les lignes d'une couche (None si absente)."""
    try:
        import duckdb

        return duckdb.connect().execute(
            f"SELECT COUNT(*) FROM read_parquet('{path}/*.parquet')"
        ).fetchone()[0]
    except Exception:
        return None


def monitoring_report(results: list[dict], total_s: float) -> None:
    """Affiche et sauvegarde un rapport d'observabilité (latence, lignes, taux d'erreur)."""
    rows = {
        "silver_trips": count_rows(f"{DATA_ROOT}/silver/trips"),
        "gold_demand_by_zone_hour": count_rows(f"{DATA_ROOT}/gold/demand_by_zone_hour"),
        "gold_tips_analysis": count_rows(f"{DATA_ROOT}/gold/tips_analysis"),
    }
    errors = sum(1 for r in results if r["statut"] != "OK")
    report = {
        "duree_totale_s": round(total_s, 1),
        "taux_erreur": f"{errors}/{len(results)}",
        "etapes": results,
        "lignes_par_couche": rows,
    }
    print("\n" + "-" * 70 + "\n📊 RAPPORT DE MONITORING\n" + "-" * 70)
    for r in results:
        print(f"  {r['statut']:6} | {r['duree_s']:6}s | tentatives={r['tentatives']} | {r['etape']}")
    print(f"  Lignes : silver={rows['silver_trips']} | "
          f"demand={rows['gold_demand_by_zone_hour']} | tips={rows['gold_tips_analysis']}")
    print(f"  Durée totale : {report['duree_totale_s']}s | Taux d'erreur : {report['taux_erreur']}")
    os.makedirs(DATA_ROOT, exist_ok=True)
    with open(f"{DATA_ROOT}/pipeline_run_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"  Rapport sauvegardé -> {DATA_ROOT}/pipeline_run_report.json")


def main() -> None:
    months = sys.argv[1:]
    t0 = time.time()
    results: list[dict] = []
    for i, (label, cmd) in enumerate(STEPS, start=1):
        full_cmd = cmd + months if cmd[1].endswith("ingest.py") else cmd
        print(f"\n{'='*70}\nÉTAPE {i}/{len(STEPS)} : {label}\n{'='*70}")
        res = run_step(label, full_cmd)
        results.append(res)
        if res["statut"] != "OK":
            alert_failure(label)
            monitoring_report(results, time.time() - t0)
            sys.exit(res.get("code", 1))
    monitoring_report(results, time.time() - t0)
    print("\n✅ PIPELINE COMPLÈTE. Données prêtes dans ./data/gold/")
    print("   -> Dashboard :  streamlit run dashboard/app.py")
    print("   -> API       :  uvicorn api.app:app --reload")


if __name__ == "__main__":
    main()

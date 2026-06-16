"""
Test automatisé (Bloc 2 — tests/intégration continue).
Vérifie que la fonction de contrôle qualité détecte bien les problèmes.
Lancer sans rien installer de plus :  python tests/test_quality.py
(Aucune dépendance à pytest : on utilise de simples assert.)
"""
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from quality.checks import run_checks  # noqa: E402


def make_df(**overrides):
    base = {
        "pickup_ts": pd.Timestamp("2024-01-01 10:00"),
        "total_amount": 20.0,
        "pu_location_id": 100,
        "trip_duration_min": 12,
        "tip_pct": 15.0,
        "pu_borough": "Manhattan",
        "driver_pseudo": "abc123",
    }
    base.update(overrides)
    return pd.DataFrame([base] * 10)


def test_donnees_propres_passent():
    results = run_checks(make_df())
    critiques_ko = [r for r in results if r["severity"] == "critical" and not r["passed"]]
    assert not critiques_ko, f"Des tests critiques échouent à tort : {critiques_ko}"


def test_detecte_total_negatif():
    df = make_df(total_amount=-5.0)
    results = {r["name"]: r["passed"] for r in run_checks(df)}
    assert results["total_amount_positif"] is False


def test_detecte_pii_en_clair():
    df = make_df()
    df["driver_email"] = "driver1@taxi.nyc"  # fuite de PII simulée
    results = {r["name"]: r["passed"] for r in run_checks(df)}
    assert results["rgpd_pas_de_pii_claire"] is False


if __name__ == "__main__":
    test_donnees_propres_passent()
    test_detecte_total_negatif()
    test_detecte_pii_en_clair()
    print("✅ Tous les tests automatisés passent.")

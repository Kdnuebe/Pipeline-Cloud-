# 6. Monitoring, alerting & qualité des données

## Indicateurs suivis (observabilité)
Un **rapport de run** est généré à chaque exécution (`data/pipeline_run_report.json`) et affiché en
console : durée et statut par étape, lignes traitées par couche, taux d'erreur. Exemple réel :

```
OK | 40.8s | tentatives=1 | BRONZE — Ingestion
OK | 10.4s | tentatives=1 | SILVER+GOLD — Transformations
OK |  3.9s | tentatives=1 | QUALITÉ — Tests
OK | 35.1s | tentatives=1 | ML — Entraînement & scoring
Lignes : silver=2 717 423 | demand=12 105 | tips=77 | Durée totale : 90s | Taux d'erreur : 0/4
```

| Indicateur (PDF) | Où on le voit |
|---|---|
| **Nb de lignes traitées** par couche | Rapport de run + `RowsProcessed` + `COUNT(*)` Athena |
| **Latence / durée** | Durée par étape (rapport de run) ; temps de requête Athena |
| **Volume de données lu** (perf + coût) | Athena « **Data scanned** » sous chaque requête |
| **Taux d'erreur** | Rapport de run (`taux_erreur`) + tests `checks.py` en échec |
| **Coût cumulé** | Console AWS **Cost Explorer / Billing** |

## Qualité des données (tests automatisés intégrés)
Module `quality/checks.py`, exécuté comme **étape dédiée** de la pipeline (entre silver et ML). Si un
test **critique** échoue, le script s'arrête (code d'erreur) → la pipeline ne continue pas avec des
données douteuses. Résultats réels (2024-01) :

| Test | Type | Résultat |
|---|---|---|
| Volume non vide | critique | ✅ 2 717 423 lignes |
| Non-null `pickup_ts`, `total_amount`, `pu_location_id` | critique | ✅ 0 null |
| `total_amount ≥ 0` | critique | ✅ |
| Durée ∈ [1, 240] min | critique | ✅ |
| `tip_pct ∈ [0,100]` | warning | ✅ 99,89 % |
| Jointure zones réussie | warning | ✅ 100 % |
| **RGPD** : pas de PII en clair en silver | critique | ✅ `driver_email` absent |

## Alerting (simple et efficace)
1. **Alerte budget (cloud)** : créer un **AWS Budget** (console → Billing → Budgets) à, par ex.,
   **5 €**, avec notification **email** à 80 % et 100 %. → démonstration directe d'une alerte cloud,
   alignée FinOps. *(Capture : la config du budget + l'email reçu si dépassement.)*
2. **Alerte qualité (pipeline)** : un test critique en échec **arrête la pipeline** et l'affiche en
   rouge dans la console → l'opérateur est immédiatement informé.

> **Pour aller plus loin** : la version `avance_optionnel/` ajoute des **métriques CloudWatch**
> personnalisées + un **tableau de bord** + des **alertes SNS** automatiques (email/Slack) sur échec
> d'exécution. Non nécessaire pour la démonstration, mais cité comme évolution.

# 4. Choix des formats de stockage & comparatifs

## Format retenu : Parquet (toutes les couches)

| Critère | CSV | **Parquet** ✅ | Delta Lake | Iceberg | ORC |
|---|---|---|---|---|---|
| Stockage (compression) | ❌ aucune | ✅ colonnaire ~5-10× | ✅ (Parquet+log) | ✅ | ✅ |
| Performance lecture Athena | ❌ scan total | ✅ pruning colonnes/partitions | ✅ | ✅ | ✅ |
| Évolutivité du schéma | ❌ | ⚠️ basique | ✅ ACID, time-travel | ✅ ACID | ⚠️ |
| Compatibilité services AWS | ✅ | ✅ natif (Athena/Glue) | ⚠️ (Athena lecture seule v3) | ✅ (Athena/Glue) | ✅ |
| Complexité opérationnelle | ✅ simple | ✅ simple | ❌ table log à gérer | ⚠️ | ✅ |
| Coût Athena (par To scanné) | ❌ élevé | ✅ faible | ✅ | ✅ | ✅ |

**Décision** : **Parquet**. Compression colonnaire native, pruning de colonnes/partitions sous
Athena (donc coût minimal), compatibilité parfaite Glue/Athena, et **déjà le format source** des
données TLC (pas de conversion en bronze). Delta/Iceberg apportent l'ACID et le time-travel, utiles
pour des mises à jour concurrentes — non nécessaires ici (ingestion append par mois), pour une
complexité et un coût supérieurs. **Iceberg serait le choix d'évolution** si l'on voulait des
upserts/time-travel.

## Stratégie de partitionnement
`bronze/trips/year=YYYY/month=MM/` — partition par **mois** :
- aligné sur la cadence de publication TLC (1 fichier/mois) ;
- permet le **pruning** Athena (ne scanner que les mois requis) ;
- granularité adaptée au volume (~3 M lignes/partition, ni trop fine ni trop grosse).

## Ingestion : incrémentale vs full load
- **Trips** : **incrémentale** — un nouveau mois = une nouvelle partition, sans retoucher l'existant.
- **Zones** (référentiel, 265 lignes, change rarement) : **full load** à chaque run (négligeable).
- **Météo** : incrémentale par mois (jointure par date en silver).

## Rétention & versionnement
- **Bronze** : conservé brut ; lifecycle S3 → **STANDARD_IA après 30 j** (FinOps), suppression
  réglable (RGPD, cf. [08_rgpd.md]).
- **Silver/Gold** : reconstructibles depuis bronze (idempotent : `DROP` + `CTAS`).
- **Résultats Athena** : expiration **7 jours** (jetables).
- **Modèle ML** : artefact horodaté `model_<run_id>.pkl` (versionnement).

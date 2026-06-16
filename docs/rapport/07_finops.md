# 7. Analyse FinOps

> Livrable central (20 %). Chiffres générés par `finops/cost_calculator.py`. **Les coûts réels seront
> relevés dans AWS Cost Explorer après la démo** et reportés ici.

## Principe directeur
**Le traitement lourd se fait en local (gratuit) ; le cloud ne sert qu'au stockage (S3) et aux
requêtes (Athena).** Résultat : un coût **quasi nul** (quelques centimes), tout en démontrant une
vraie architecture cloud. L'objectif est de **maîtriser** les coûts, pas de dépenser.

## 1. Facturation développement & recette

| Poste | Coût (USD) |
|---|---|
| Stockage S3 (0,3 Go, 1 mois) | 0.0069 |
| Athena — reconstructions silver/gold (20 ×) | 0.0117 |
| Athena — requêtes d'exploration | 0.0049 |
| S3 — uploads | 0.0010 |
| **TOTAL dev/recette** | **≈ 0.025 USD** |

*(Le développement du code se fait 100 % en local → 0 €.)*

## 2. Facturation exploitation (run mensuel)

| Poste | Coût (USD) |
|---|---|
| Stockage S3 | 0.0069 |
| Athena — reconstructions (8/mois) | 0.0047 |
| Athena — exploration (100 requêtes) | 0.0049 |
| **TOTAL mensuel** | **≈ 0.017 USD** |

**Extrapolation : ~0,02 USD/mois → ~0,20 USD/an.** Très loin des 50 €.

## 3. Comparatifs AVANT chaque choix de service

### Moteur de traitement : Athena vs Glue Spark vs EMR
| Critère | **Athena** ✅ | Glue Spark | EMR |
|---|---|---|---|
| Coût (volume projet) | ✅ 5 $/To scanné → cents | ⚠️ 0,44 $/DPU-h, min 2 DPU | ❌ cluster à l'heure |
| Complexité | ✅ SQL pur, serverless | ⚠️ PySpark + job | ❌ cluster à gérer |
| Maîtrise / explicabilité | ✅ on lit le SQL | ⚠️ | ❌ |
| **Décision** | **Retenu** : le plus simple ET le moins cher au volume du projet. | Surdimensionné. | Rédhibitoire. |

### Requête : Athena vs Redshift vs BigQuery
| Critère | **Athena** ✅ | Redshift | BigQuery (GCP) |
|---|---|---|---|
| Coût | ✅ payé à la requête | ❌ cluster facturé même au repos | ⚠️ payé requête (hors AWS) |
| Intégration S3 | ✅ native | ⚠️ Spectrum | ❌ |
| **Décision** | **Retenu** : serverless, idéal data lake S3. | Cher au repos. | Hors AWS. |

### Stockage : Parquet vs CSV vs Delta/Iceberg
→ voir [04_formats_stockage.md]. **Décision : Parquet** (compressé, colonnaire → Athena scanne moins
→ coût minimal).

### Dashboard : Streamlit vs Metabase vs QuickSight
| Critère | **Streamlit** ✅ | Metabase | QuickSight |
|---|---|---|---|
| Coût | ✅ gratuit | ✅ gratuit (self-host) | ❌ payant/utilisateur |
| Mise en place | ✅ 1 fichier Python | ⚠️ conteneur | ✅ managé |
| **Décision** | **Retenu** : gratuit, simple, lit directement le gold. | Alternative. | Payant. |

### Orchestration : script Python vs Airflow vs Step Functions
→ voir [05_orchestration.md]. **Décision : script Python** (gratuit, maîtrisé).

## 4. Optimisations FinOps
| Optimisation | Effet |
|---|---|
| **Parquet + partitionnement** | Athena scanne moins de données → coût requête réduit |
| **Traitement lourd en local** | 0 € de compute cloud (vs Glue/EMR) |
| **Lifecycle S3** (Standard → IA → Glacier) | -40 à -80 % sur le stockage ancien |
| **Suppression du bucket après la démo** | Coût ramené à 0 |
| **Athena « Data scanned »** suivi par requête | Pilotage direct du coût |

**Coût avec vs sans optimisations** : ~**0,02 $/mois** (version simple optimisée) contre ~**3-4 $/mois**
pour la version industrialisée (Glue + Step Functions, cf. `avance_optionnel/`), elle-même contre
~**15-25 $/mois** sans aucune optimisation (Glue Spark + runs forcés).

## 5. Free tiers & limites
- **AWS Free Tier** : S3 (5 Go gratuits/12 mois) couvre largement le stockage du projet.
- **Athena** : pas de free tier, mais coût négligeable ici (quelques Mo scannés → fractions de centime).
- **AWS Educate / crédits étudiants** : à activer si disponibles.
- **Où démarrent les coûts** : dès le 1er Go scanné par Athena (~0,005 $) et le stockage au-delà du
  free tier S3 (~0,023 $/Go/mois). Concrètement : **centimes**.

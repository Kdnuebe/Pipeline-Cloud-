# 🎬 Script de la vidéo de présentation (10-15 min)

Enregistre ton écran (OBS Studio, gratuit) + voix. Prépare les onglets à l'avance. Vise **~13 min**.
Parle simplement : tu dois montrer que **tu maîtrises** chaque étape.

---

## 1. Introduction — thématique, données, problématiques (2 min)
- « Pipeline médaillon **Bronze → Silver → Gold** sur le cloud AWS, sur les **taxis jaunes de NYC**. »
- Montre les 3 sources (TLC ~3 M lignes/mois, zones, météo) → **> 1 M lignes**.
- Énonce les **3 problématiques** : demande/revenus, pourboires, prédiction ML.
- *Appui :* `docs/rapport/00_resume_executif.md` (l'analogie de la cuisine pour un public non technique).

## 2. Architecture & choix (3 min)
- Affiche le **diagramme** (`architecture.mmd`).
- Explique l'idée médaillon + les **2 services cloud** : **S3** (stockage) et **Athena** (SQL distribué).
- Insiste sur le **choix de simplicité** : pas de Glue/Step Functions/Terraform → on maîtrise tout.
- *Appui :* `docs/rapport/03_architecture.md`.

## 3. Démo live de la pipeline (3 min)
- **En local** : lance `python run_local_pipeline.py 2024-01` → montre les volumes (2,9 M → 2,7 M),
  les **9 tests qualité** verts, le **ML +77 %**, et le **rapport de monitoring** (durées, taux d'erreur).
- **Orchestration cloud** : montre le **graphe Step Functions** au vert (Silver → Gold) — l'orchestrateur.
- **Dans le cloud (Athena)** : montre les tables `bronze/silver/gold` puis exécute une requête de
  `04_explore.sql` → résultat + le **« Data scanned »** (indicateur coût/perf).

## 4. Gold : dashboard, API & valeur métier (3 min)
- **Dashboard** Streamlit : 3 onglets (top zones JFK/LaGuardia/Midtown, heatmap, pourboires carte vs
  espèces, prédictions).
- **API** : ouvre `/docs` (Swagger), teste `/zones/top` et `/ml/metrics`.
- **ML** : « MAE 3,09 $ vs 13,96 $ baseline = **−78 %**, R² 0,92 ; la distance explique l'essentiel. »

## 5. Sécurité, FinOps & blocs (2 min)
- **Sécurité/RGPD** : montre `silver_trips` dans Athena → `driver_pseudo` **haché**, pas d'email ;
  chiffrement S3 activé ; k-anonymat en gold.
- **FinOps** : `python finops/cost_calculator.py` → **~0,02 $/mois** ; montre l'**alerte budget AWS**.
- **Conclusion** : « Le projet valide le **Bloc 3** en entier et l'essentiel du **Bloc 2** (cf. mapping
  compétences). Stack simple, maîtrisée, coût quasi nul, entièrement reproductible. »

---

### Checklist avant d'enregistrer
- [ ] Onglets ouverts : terminal (pipeline locale), console S3, console Athena, Dashboard, Swagger, Budgets/Cost Explorer
- [ ] Pipeline locale déjà testée + données uploadées sur S3 + tables Athena créées
- [ ] Alerte budget AWS configurée (capture de l'email si possible)
- [ ] Repli local prêt si l'AWS coince : `python run_local_pipeline.py 2024-01`
```

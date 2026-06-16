# 9. Interprétations métier & réponses aux problématiques

*Résultats réels mesurés sur le mois 2024-01 (2 717 423 courses valides après nettoyage).*

## Problématique 1 — Demande & revenus
- **Pics de demande** en fin d'après-midi : **18 h (≈195 k courses), 17 h, 16 h** → heures de pointe
  du soir. À exploiter pour l'affectation des chauffeurs.
- **Zones les plus rentables** : **JFK Airport (≈11,0 M$), LaGuardia Airport (≈5,7 M$), Midtown
  Center** → les aéroports dominent par le ticket moyen, Midtown par le volume.
- **Revenu par arrondissement** : **Manhattan ≈ 55,1 M$**, **Queens ≈ 17,8 M$** (effet aéroports),
  Brooklyn/Bronx marginaux → forte concentration géographique.

> Exposé via : `GET /zones/top`, `GET /demand?borough=&hour=` et l'onglet « Demande » du dashboard
> (heatmap heure × jour).

## Problématique 2 — Pourboires
- **Carte bancaire (payment_type=1) : ≈ 16,2 % de pourboire moyen** ; **espèces : 0 %** —
  artefact connu : les pourboires en espèces ne sont **pas enregistrés** par le compteur. Insight
  important pour ne pas mésinterpréter la donnée.
- **Effet météo léger** : pourboire moyen légèrement supérieur les jours de **pluie (5,16 %)** vs
  **sec (4,98 %)** sur les segments — corrélation faible mais réelle.

> Exposé via : `GET /tips` et l'onglet « Pourboires » du dashboard.

## Problématique 3 — Prédiction & anomalies (ML)
- **Régression du montant total** : **MAE 3,10 $** (modèle) contre **13,89 $** (baseline = moyenne),
  soit **−77,7 %** d'erreur ; **R² = 0,918**.
- **Variable la plus prédictive** : `trip_distance` (importance **0,93**) — logique : la distance
  détermine l'essentiel du tarif.
- **Détection d'anomalies** : ~**175** courses atypiques (sur 10 000 exposées) repérées par
  IsolationForest (montants/durées incohérents) → pistes de fraude/erreurs de facturation.

> Exposé via : `GET /predictions`, `GET /ml/metrics` et l'onglet « Prédictions ML » du dashboard.

## Synthèse
La pipeline répond aux 3 problématiques avec des résultats **cohérents et exploitables**, depuis la
donnée brute jusqu'à des datamarts agrégés, une API et un dashboard — le tout reproductible
localement (gratuit) et déployable sur AWS.

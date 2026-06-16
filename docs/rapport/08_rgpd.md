# 8. Conformité RGPD

## Contexte
Les données TLC publiques ne contiennent **pas de PII directe** (GPS retirés ; seulement des
`LocationID` = zones, donc déjà généralisées). Pour traiter le sujet de façon **démonstrative**,
on injecte à l'ingestion un identifiant chauffeur **synthétique** (`driver_email`) que l'on protège
tout au long de la pipeline.

## 1. Cartographie des données sensibles (Data Mapping)

| Champ | Catégorie RGPD | Niveau | Action appliquée |
|---|---|---|---|
| `driver_email` (synthétique) | Identification directe | Élevé | **Pseudonymisation** (SHA-256 salé) dès silver ; clair jamais propagé |
| `PULocationID` / `DOLocationID` | Localisation (indirecte) | Moyen | **Généralisation** native (zone, pas de GPS) + k-anonymat en gold |
| Combinaison zone × heure × date | Ré-identification possible | Moyen | **k-anonymat (k ≥ 5)** sur les agrégats gold |
| Montants, distances | Comportementales | Faible | Agrégation en gold |

## 2. Techniques de protection retenues (comparatif)

| Technique | Où | Réversible | Pourquoi ici |
|---|---|---|---|
| **Pseudonymisation** (SHA-256 + sel) | bronze → silver | Non (sel secret) | Protéger `driver_email` tout en gardant la possibilité d'analyses par chauffeur pseudonyme |
| **Chiffrement au repos** (SSE-S3 / KMS) | toutes couches S3 | Oui (clé) | Confidentialité du stockage brut |
| **Généralisation** | localisation | Non | Zones au lieu de GPS |
| **k-anonymat (k ≥ 5)** | agrégats gold | Non | Empêcher la ré-identification via mailles fines (`HAVING COUNT(*) >= 5`) |
| **Contrôle d'accès** (IAM, rate limiting API) | bronze + API | — | Bronze non exposé ; API limitée (throttling) |

> Alternatives écartées pour ce cas : *hachage simple sans sel* (vulnérable aux dictionnaires),
> *differential privacy* (overkill au vu des enjeux), *anonymisation totale* (perdrait l'analyse).

## 3. Application par couche médaillon

| Couche | Mesures concrètes (où dans le code) |
|---|---|
| **Bronze** | **Chiffrement SSE-S3** activé à la création du bucket (commande en guide Partie 4) ; **accès IAM restreint** (utilisateur dédié, droits S3+Athena seulement) ; bucket **non public** (par défaut sur S3) ; `driver_email` en clair toléré (brut) mais inaccessible publiquement |
| **Silver** | **Pseudonymisation** : `silver_trips.sql` ne sélectionne que `driver_pseudo` (le clair est exclu) ; test qualité `rgpd_pas_de_pii_claire` vérifie l'absence de `driver_email` ; généralisation des zones |
| **Gold** | **k-anonymat** (`HAVING COUNT(*) >= 5`) dans les datamarts ; API & dashboard : **aucune donnée identifiante** exposée (uniquement des agrégats anonymes) |

Le **sel de pseudonymisation** (`PSEUDO_SALT`) est stocké hors données (fichier `.env`, variable
d'environnement), jamais publié ni versionné.

## 4. Exigences documentaires

### Registre de traitement (simplifié)
| Élément | Valeur |
|---|---|
| Finalité | Analyse statistique de la mobilité taxi (demande, revenus, pourboires, prévision) |
| Base légale | Intérêt légitime / données ouvertes ; champ PII synthétique à but pédagogique |
| Catégories de données | Courses (horodatage, montants), zones, météo, identifiant chauffeur pseudonymisé |
| Destinataires | Équipe projet (lecture), API publique (agrégats anonymes uniquement) |
| Durée de rétention | Bronze 30 j → IA puis suppression ; Gold conservé ; résultats Athena 7 j |
| Mesures de sécurité | SSE-S3, IAM least-privilege, pseudonymisation, k-anonymat, rate limiting |

### Politique de rétention & droit à l'effacement
- Cycle de vie S3 (`cloud_simple/s3_lifecycle.json`) : bronze → STANDARD_IA (30 j) → Glacier (90 j) ;
  résultats Athena expirés à 7 j.
- **Effacement** : suppression de la partition bronze concernée + reconstruction silver/gold
  (idempotente). La table de correspondance pseudonyme n'existe pas (hachage non réversible),
  donc pas de re-liaison possible.

### Gestion des clés de chiffrement
- SSE-S3 (clés gérées par AWS) par défaut ; **évolution recommandée : SSE-KMS** avec clé dédiée
  (`AWS KMS`), rotation annuelle automatique, révocation via politique de clé.

### AIPD (analyse d'impact) — simplifiée
Aucune donnée de **catégorie art. 9** (santé, opinions…) n'est présente → AIPD non requise. Le seul
champ « personnel » est synthétique et pseudonymisé dès silver : risque résiduel **faible**.

> Outils complémentaires possibles : **Amazon Macie** ou **Microsoft Presidio** pour la détection
> automatique de PII ; **AWS KMS** pour les clés ; **Lake Formation** pour le contrôle d'accès fin.

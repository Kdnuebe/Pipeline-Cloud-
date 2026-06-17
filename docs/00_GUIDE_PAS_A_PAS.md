# 🧭 Guide pas-à-pas (version SIMPLE — à maîtriser de A à Z)

Ce guide mène de zéro à un projet qui tourne, **sans Terraform ni outil compliqué**. Le cloud se
limite à des services simples : **S3** (stockage), **Athena** (SQL) et **Step Functions**
(orchestration). Tout se fait dans la **console AWS** + quelques commandes — ou en **une seule commande**
automatisée (voir Partie 5).

**Plan :**
- [Partie 0 — Installer](#p0)
- [Partie 1 — Pipeline en LOCAL (gratuit)](#p1)
- [Partie 2 — Dashboard & API en local](#p2)
- [Partie 3 — Préparer AWS (compte + accès)](#p3)
- [Partie 4 — S3 : stocker dans le cloud](#p4)
- [Partie 5 — Athena : transformer dans le cloud (SQL)](#p5)
- [Partie 5 bis — Orchestrer avec Step Functions](#p5bis)
- [Partie 6 — Sécurité & RGPD](#p6)
- [Partie 7 — Coûts & nettoyage](#p7)
- [Dépannage](#depannage)

> ⚡ **Le plus rapide (tout automatisé)** : après `aws configure`, une seule commande déploie tout
> (S3 + Athena + Step Functions + exécution) :
> `python cloud_simple/deploy.py --email ton@email.com`. Les parties 4 et 5 ci-dessous détaillent
> la version manuelle (utile pour comprendre et faire des captures).

---

## <a name="p0"></a>Partie 0 — Installer (10 min)

| Outil | Pourquoi | Déjà installé chez toi ? |
|---|---|---|
| **Python 3.12** | le code de la pipeline | ✅ oui |
| **AWS CLI v2** | parler à AWS en ligne de commande | ✅ oui |
| Un **compte AWS** | héberger S3 + Athena | à créer (Partie 3) |

> 🎉 Bonne nouvelle : **plus besoin de Terraform**. Tu n'installes rien de plus.

---

## <a name="p1"></a>Partie 1 — Pipeline en LOCAL (gratuit, ~2 min)

Ouvre un terminal **dans le dossier du projet** (`Pipeline Cloud`).

```powershell
python -m venv .venv
.\.venv\Scripts\activate            # le prompt affiche (.venv)
pip install -r requirements.txt
copy .env.example .env

python run_local_pipeline.py 2024-01     # bronze -> silver -> gold -> qualité -> ML
```
Tu obtiens les 3 couches dans `data/bronze`, `data/silver`, `data/gold`.
**Capture utile :** la console (volumes 2,9 M → 2,7 M, 9 tests qualité ✅, ML +77 %).

> Pour le rapport (≥ 1 M lignes + partitionnement) : `python run_local_pipeline.py 2024-01 2024-02 2024-03`

---

## <a name="p2"></a>Partie 2 — Dashboard & API en local

```powershell
streamlit run dashboard/app.py            # http://localhost:8501  (3 onglets)
```
```powershell
# dans un AUTRE terminal (.venv activé)
uvicorn api.app:app --reload              # http://localhost:8000/docs  (Swagger)
```
**Captures :** les 3 onglets du dashboard + la page Swagger `/docs`.

> L'API tourne en local : c'est suffisant pour la démo et facile à expliquer.

---

## <a name="p3"></a>Partie 3 — Préparer AWS (une seule fois)

1. Crée un compte sur https://aws.amazon.com (carte requise mais on restera en quasi-gratuit ;
   utilise AWS Educate / crédits étudiants si dispo).
2. Console AWS → service **IAM** → **Utilisateurs** → crée un utilisateur (ex. `etudiant`) avec
   **clés d'accès** (Access key + Secret key). Donne-lui les droits `AmazonS3FullAccess` et
   `AmazonAthenaFullAccess` (suffisant pour le projet).
3. Configure le CLI :
   ```powershell
   aws configure
   # AWS Access Key ID     : <ta clé>
   # AWS Secret Access Key : <ton secret>
   # Default region name   : eu-west-3
   # Default output format : json
   ```
   Test : `aws sts get-caller-identity` → doit afficher ton numéro de compte.

---

## <a name="p4"></a>Partie 4 — S3 : stocker dans le cloud

> S3 = le « disque dur du cloud ». On y dépose les fichiers de la pipeline.

**Choisis un nom de bucket UNIQUE au monde** (ex. `nyc-taxi-tonprenom-2026`). Remplace
`VOTRE-BUCKET` partout par ce nom.

```powershell
# 1) Créer le bucket
aws s3 mb s3://VOTRE-BUCKET --region eu-west-3

# 2) Activer le chiffrement au repos (sécurité RGPD)
aws s3api put-bucket-encryption --bucket VOTRE-BUCKET --server-side-encryption-configuration "{\"Rules\":[{\"ApplyServerSideEncryptionByDefault\":{\"SSEAlgorithm\":\"AES256\"}}]}"

# 3) Uploader la couche bronze (données brutes)
aws s3 cp data/bronze s3://VOTRE-BUCKET/bronze --recursive

# 4) Uploader les prédictions ML (calculées en local)
aws s3 cp data/gold/ml_predictions s3://VOTRE-BUCKET/gold/ml_predictions --recursive

# 5) Politique de cycle de vie (archivage = optimisation stockage)
aws s3api put-bucket-lifecycle-configuration --bucket VOTRE-BUCKET --lifecycle-configuration file://cloud_simple/s3_lifecycle.json
```

**Captures :** la console S3 montrant le dossier `bronze/` + l'onglet « Management » (lifecycle) +
« Properties » (Encryption: Enabled).

> Tu peux aussi tout faire **à la souris** dans la console S3 (Create bucket → Upload). La console
> est plus visuelle pour comprendre et pour les captures.

---

## <a name="p5"></a>Partie 5 — Athena : transformer dans le cloud (SQL)

> Athena = un moteur qui exécute du **SQL sur les fichiers S3**, sans serveur. **C'est ici que le
> cloud fait le traitement** (nettoyage, jointures, agrégats).

1. Console AWS → **Athena** → Éditeur de requêtes.
2. La 1re fois : Athena demande un « query result location » → mets `s3://VOTRE-BUCKET/athena-results/`
   (Settings → Manage → Browse).
3. Ouvre le fichier `cloud_simple/athena/01_create_bronze_tables.sql`, **remplace `VOTRE-BUCKET`**
   par ton bucket, copie-colle dans Athena, **Exécute**. (Tables bronze créées.)
4. Pareil avec `02_build_silver.sql` (le cloud nettoie + joint + pseudonymise → table `silver_trips`).
5. Pareil avec `03_build_gold.sql` (datamarts `demand_by_zone_hour`, `tips_analysis`, + table ML).
6. `04_explore.sql` : lance les requêtes métier → **réponses aux 3 problématiques** + captures.

**À noter pour le rapport :** sous chaque requête, Athena affiche « **Data scanned** » (Mo lus) =
indicateur de **coût** et de **performance**. C'est ton optimisation FinOps (Parquet = peu scanné).

**Captures :** liste des tables (bronze/silver/gold) dans Athena + un résultat de `04_explore.sql`
(ex. top zones JFK/LaGuardia/Midtown) + le « Data scanned ».

---

## <a name="p5bis"></a>Partie 5 bis — Orchestrer avec Step Functions (recommandé)

Au lieu de lancer les scripts Athena `02`/`03` à la main, **AWS Step Functions** les enchaîne
**automatiquement** (l'orchestrateur cité dans le sujet). Tu obtiens un **graphe visuel** qui passe au
vert, et une **alerte email** en cas d'échec.

**Pré-requis :** avoir exécuté `01_create_bronze_tables.sql` (tables bronze créées) et avoir les
dossiers `silver/` et `gold/` **vides**.

Mise en place en quelques commandes (remplace `VOTRE-BUCKET` et ton email) :
```powershell
$BUCKET="VOTRE-BUCKET"; $EMAIL="ton@email.com"
$ACCOUNT=(aws sts get-caller-identity --query Account --output text)

# 1) Topic SNS d'alerte + abonnement (clique le lien reçu par email !)
$TOPIC=(aws sns create-topic --name nyc-taxi-alerts --query TopicArn --output text)
aws sns subscribe --topic-arn $TOPIC --protocol email --notification-endpoint $EMAIL

# 2) Rôle IAM pour Step Functions
aws iam create-role --role-name nyc-taxi-sfn-role --assume-role-policy-document file://cloud_simple/stepfunctions/iam_trust.json
(Get-Content cloud_simple/stepfunctions/iam_policy.json) -replace "VOTRE-BUCKET",$BUCKET -replace "VOTRE_SNS_TOPIC_ARN",$TOPIC | Set-Content policy_tmp.json
aws iam put-role-policy --role-name nyc-taxi-sfn-role --policy-name perms --policy-document file://policy_tmp.json
$ROLE="arn:aws:iam::$($ACCOUNT):role/nyc-taxi-sfn-role"

# 3) Créer puis lancer la state machine
(Get-Content cloud_simple/stepfunctions/state_machine.asl.json) -replace "VOTRE-BUCKET",$BUCKET -replace "VOTRE_SNS_TOPIC_ARN",$TOPIC | Set-Content sm_tmp.json
$SM=(aws stepfunctions create-state-machine --name nyc-taxi-pipeline --definition file://sm_tmp.json --role-arn $ROLE --query stateMachineArn --output text)
aws stepfunctions start-execution --state-machine-arn $SM
```
Puis regarde le **graphe** dans la console Step Functions (Silver → Gold) passer au vert.

**Capture :** le graphe d'exécution Step Functions au vert.

> 💡 Tout ceci (et les parties 4-5) est fait **en une commande** par `python cloud_simple/deploy.py
> --email ton@email.com`. Pour relancer la state machine : supprime les tables silver/gold et vide
> leurs dossiers S3 (voir Dépannage).

---

## <a name="p6"></a>Partie 6 — Sécurité & RGPD (Bloc 3)

À montrer (et expliquer en soutenance) :
- **Chiffrement** : activé en Partie 4 (SSE-S3). Console S3 → Properties → « Encryption: Enabled ».
- **IAM (gestion des accès)** : tu as créé un utilisateur avec des droits limités (S3 + Athena
  seulement). Explique le principe du **moindre privilège**.
- **RGPD dans la donnée** : ouvre `silver_trips` dans Athena → la colonne `driver_pseudo` est
  **hachée** (pas d'email en clair) ; les datamarts gold appliquent le **k-anonymat** (≥ 5 courses).

**Capture :** la table `silver_trips` (colonne `driver_pseudo` hachée, pas de `driver_email`).

---

## <a name="p7"></a>Partie 7 — Coûts & nettoyage

- **Coûts réels** : Console → **Billing / Cost Explorer** (le lendemain) — quelques centimes.
- **Estimation** : `python finops/cost_calculator.py`.
- **Nettoyer** (pour ne plus rien payer) quand tu as fini :
  ```powershell
  aws s3 rb s3://VOTRE-BUCKET --force      # supprime le bucket et son contenu
  ```
  (Dans Athena, tu peux aussi faire `DROP DATABASE nyc_taxi CASCADE;`.)

---

## <a name="depannage"></a>Dépannage

| Problème | Solution |
|---|---|
| `aws: command not found` | AWS CLI pas dans le PATH ; rouvre le terminal. |
| Athena : « query result location » | Mets `s3://VOTRE-BUCKET/athena-results/` dans Settings. |
| Athena table vide / 0 ligne | Vérifie l'upload S3 (Partie 4) et que `VOTRE-BUCKET` est bien remplacé. |
| `CREATE TABLE ... already exists` | `DROP TABLE nyc_taxi.<table>;` puis vide le dossier S3 correspondant, relance. |
| Bucket name already exists | Choisis un autre nom (doit être unique au monde). |
| Console Python plante sur un emoji (Windows) | Déjà géré (UTF-8). Sinon `set PYTHONUTF8=1`. |

> **Filet de sécurité** : si l'AWS coince le jour J, la démo locale
> (`python run_local_pipeline.py 2024-01` + dashboard + API) marche à 100 % et suffit à montrer
> toute la pipeline. Le cloud (S3 + Athena) vient en complément pour le Bloc 3.

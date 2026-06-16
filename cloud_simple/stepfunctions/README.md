# ⚙️ Orchestration cloud SIMPLE avec AWS Step Functions

Step Functions **orchestre les transformations Athena** (silver → gold) dans le cloud, **sans
Terraform, sans Glue, sans Lambda**. Tu obtiens un **graphe visuel** qui passe au vert (idéal pour la
soutenance) et l'outil d'orchestration **nommé dans le PDF**.

> Rappel du partage des rôles : **ingestion + ML restent en local** (Python, que tu maîtrises),
> Step Functions s'occupe uniquement des **transformations Athena**. Les fichiers `*.asl.json` et
> `iam_*.json` ici sont prêts à l'emploi (remplace juste `VOTRE-BUCKET` et `VOTRE_SNS_TOPIC_ARN`).

## Pré-requis
1. Avoir uploadé `data/bronze` vers S3 et **exécuté `athena/01_create_bronze_tables.sql`** (les tables
   `bronze_*` doivent exister).
2. Les dossiers `s3://VOTRE-BUCKET/silver/` et `s3://VOTRE-BUCKET/gold/` doivent être **vides**
   (sinon le `CREATE TABLE` échouera — voir « Relancer » plus bas).

---

## Option A — Tout en ligne de commande (rapide, reproductible)

```powershell
# 0) Variables (adapte VOTRE-BUCKET et ton email)
$BUCKET = "VOTRE-BUCKET"
$EMAIL  = "ton.email@exemple.com"
$ACCOUNT = (aws sts get-caller-identity --query Account --output text)

# 1) Créer le topic SNS d'alerte + s'y abonner (clique le lien reçu par email !)
$TOPIC = (aws sns create-topic --name nyc-taxi-alerts --query TopicArn --output text)
aws sns subscribe --topic-arn $TOPIC --protocol email --notification-endpoint $EMAIL

# 2) Créer le rôle IAM que Step Functions va endosser
aws iam create-role --role-name nyc-taxi-sfn-role --assume-role-policy-document file://cloud_simple/stepfunctions/iam_trust.json
#   (préparer la policy en remplaçant les placeholders)
(Get-Content cloud_simple/stepfunctions/iam_policy.json) -replace "VOTRE-BUCKET", $BUCKET -replace "VOTRE_SNS_TOPIC_ARN", $TOPIC | Set-Content policy_tmp.json
aws iam put-role-policy --role-name nyc-taxi-sfn-role --policy-name perms --policy-document file://policy_tmp.json
$ROLE = "arn:aws:iam::$($ACCOUNT):role/nyc-taxi-sfn-role"

# 3) Préparer la définition (remplacer les placeholders)
(Get-Content cloud_simple/stepfunctions/state_machine.asl.json) -replace "VOTRE-BUCKET", $BUCKET -replace "VOTRE_SNS_TOPIC_ARN", $TOPIC | Set-Content sm_tmp.json

# 4) Créer la state machine
$SM = (aws stepfunctions create-state-machine --name nyc-taxi-pipeline --definition file://sm_tmp.json --role-arn $ROLE --query stateMachineArn --output text)

# 5) Lancer l'exécution (puis regarder le graphe dans la console Step Functions)
aws stepfunctions start-execution --state-machine-arn $SM
```

> Astuce : attends ~30 s après la création du rôle avant l'étape 4 (le temps que l'IAM se propage).

---

## Option B — À la souris dans la console (plus visuel, pour comprendre)
1. **SNS** : console SNS → Create topic (Standard) `nyc-taxi-alerts` → Create subscription (Email,
   ton adresse) → **confirme le lien reçu par email**.
2. **IAM** : console IAM → Roles → Create role → Trusted entity « Step Functions » → attache une
   policy avec le contenu de `iam_policy.json` (remplace `VOTRE-BUCKET` et l'ARN du topic).
3. **Step Functions** : console → Create state machine → « Write your workflow in code » → colle le
   contenu de `state_machine.asl.json` (remplace `VOTRE-BUCKET` et `VOTRE_SNS_TOPIC_ARN`) → choisis le
   rôle créé → Create.
4. **Run** : bouton « Start execution » (input vide `{}`) → regarde le **graphe** passer au vert.

---

## Vérifier / capturer
- Console Step Functions : le **graphe d'exécution** (BuildSilver → BuildGoldDemand → BuildGoldTips →
  Success) au **vert** → capture pour le rapport/la vidéo.
- Athena : les tables `silver_trips`, `demand_by_zone_hour`, `tips_analysis` sont créées.

## Démontrer l'alerte d'échec (pour le critère monitoring/alerting)
Lance l'exécution **sans** avoir vidé les dossiers (ou sans avoir créé les tables bronze) → une étape
échoue → le graphe montre `NotifyFailure` → tu **reçois un email SNS**. C'est ta démonstration d'alerte.

## Relancer proprement
Dans Athena : `DROP TABLE silver_trips; DROP TABLE demand_by_zone_hour; DROP TABLE tips_analysis;`
puis, dans la console S3, **vide** les dossiers `silver/` et `gold/demand_by_zone_hour/` et
`gold/tips_analysis/`. Relance ensuite l'exécution.

## Nettoyage
```powershell
aws stepfunctions delete-state-machine --state-machine-arn $SM
aws iam delete-role-policy --role-name nyc-taxi-sfn-role --policy-name perms
aws iam delete-role --role-name nyc-taxi-sfn-role
aws sns delete-topic --topic-arn $TOPIC
Remove-Item policy_tmp.json, sm_tmp.json
```

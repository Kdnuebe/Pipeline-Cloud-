# 0. Résumé exécutif (pour un lecteur non technique)

## En une phrase
On a construit une **chaîne de traitement de données** qui part de millions de trajets de taxis new-yorkais
bruts et les transforme, étape par étape, en **tableaux de bord et indicateurs prêts à la décision**,
le tout hébergé dans le **cloud** et pour un coût de **quelques centimes**.

## L'analogie de la cuisine (architecture « médaillon »)
Imaginez un restaurant qui transforme des ingrédients bruts en plats servis :

| Couche | Analogie cuisine | Dans le projet |
|---|---|---|
| 🥉 **Bronze** | Les **courses du marché**, livrées telles quelles | Données brutes des taxis, stockées sans modification |
| 🥈 **Silver** | Les ingrédients **lavés, épluchés, découpés** | Données nettoyées, corrigées, enrichies (météo, quartiers) |
| 🥇 **Gold** | Les **plats dressés**, prêts à servir | Tableaux de bord, indicateurs, prédictions |

Chaque couche améliore la précédente. On ne sert jamais des légumes terreux au client : on ne montre
que la couche « Gold », propre et agrégée.

## Les questions auxquelles le projet répond
1. **Où et quand** y a-t-il le plus de courses et de revenus ? *(ex. : pics à 18 h, aéroports JFK/LaGuardia en tête)*
2. **Qu'est-ce qui fait varier les pourboires ?** *(ex. : carte bancaire ≈ 16 % vs espèces 0 %)*
3. **Peut-on prédire le prix d'une course** et repérer les anomalies ? *(oui : erreur réduite de 78 %)*

## Ce qu'on a utilisé (expliqué simplement)
- **Le cloud Amazon (AWS)** : on loue de l'espace et de la puissance de calcul à la demande, on ne
  paie que ce qu'on utilise.
  - **S3** = un disque dur dans le cloud (on y range les fichiers).
  - **Athena** = un moteur qui répond à des questions en langage **SQL** directement sur ces fichiers.
- **Une « intelligence artificielle » légère** (modèle d'apprentissage automatique) qui apprend des
  trajets passés pour estimer le prix d'une nouvelle course.
- **Un tableau de bord** interactif et une **interface (API)** pour consulter les résultats.

## La sécurité et la vie privée (RGPD)
Même sur des données publiques, on a appliqué les bonnes pratiques : les **données stockées sont
chiffrées**, l'**identité du chauffeur est masquée** (rendue anonyme), les accès sont **restreints**,
et les statistiques publiées ne permettent **pas d'identifier** un individu (on regroupe par paquets
d'au moins 5 courses).

## Les résultats clés
- **~3 millions de courses** traitées en **moins de 2 minutes**.
- **9 contrôles de qualité** automatiques, tous au vert.
- Modèle de prédiction **4× plus précis** qu'une estimation naïve.
- **Coût total : quelques centimes** — l'objectif n'était pas de dépenser, mais de **maîtriser** les coûts.

## Pourquoi c'est solide
Tout a été **testé et validé** de bout en bout. La chaîne est **reproductible** (on peut tout relancer)
et **réversible** (on peut tout supprimer et arrêter les coûts en une commande). Le détail technique
suit dans les sections 1 à 9 ; la correspondance avec les compétences du diplôme est en section
« Mapping compétences ».

> **Glossaire express** — *Pipeline* : chaîne de traitement automatique. *Cloud* : informatique louée
> à distance. *SQL* : langage pour interroger des données. *Datamart* : table de résultats prête à
> l'usage. *RGPD* : règlement européen sur la protection des données personnelles. *FinOps* : maîtrise
> des coûts du cloud. *ML / IA* : programme qui apprend à partir d'exemples.

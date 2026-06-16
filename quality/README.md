# Qualité des données

## Ce qui est branché dans la pipeline
`checks.py` — **tests de qualité automatisés** exécutés comme tâche dédiée (entre silver et ML),
en local **et** sur AWS (job Glue). Un échec critique arrête la pipeline et déclenche une alerte SNS.
Le cahier des charges accepte explicitement les *custom checks* : c'est notre solution principale,
validée (9/9 tests verts sur 2024-01).

## Aller plus loin (optionnel, vitrine) : Great Expectations
Pour ajouter une suite Great Expectations « documentée » en plus :

```bash
pip install -r requirements-extra.txt
```

Puis créer une suite équivalente à nos checks (chaque `check_*` correspond à une *expectation* :
`expect_column_values_to_not_be_null`, `expect_column_values_to_be_between`,
`expect_table_row_count_to_be_between`, etc.). Ce n'est pas requis pour valider l'exigence qualité,
mais peut apporter des points « vitrine ».

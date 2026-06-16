# Conteneurisation (Bloc 2) — empaquette toute la pipeline dans une image Docker.
# Construire :  docker build -t taxi-pipeline .
# Lancer     :  docker run --rm -v ${PWD}/data:/app/data taxi-pipeline
# (Le -v partage le dossier data/ pour récupérer les résultats sur ta machine.)
FROM python:3.12-slim

WORKDIR /app

# 1) Dépendances (couche mise en cache tant que requirements.txt ne change pas)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 2) Code du projet
COPY . .

# 3) Au démarrage : exécute toute la pipeline sur 1 mois
CMD ["python", "run_local_pipeline.py", "2024-01"]

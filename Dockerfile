# Utiliser une image de base officielle Python
FROM python:3.12-slim

# Définir le répertoire de travail dans le conteneur
WORKDIR /app

# Copier le fichier requirements.txt et installer les dépendances
COPY requirements.txt .

# Installer les dépendances Python
RUN pip install --no-cache-dir -r requirements.txt

# Copier le reste du code de l'application
COPY . .

# Définir les variables d'environnement pour éviter les problèmes d'entrée en mode interactif
ENV PYTHONUNBUFFERED=1

# Commande pour exécuter l'application
CMD ["python", "main.py"]

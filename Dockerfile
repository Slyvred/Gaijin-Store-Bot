# Définir les variables d'environnement pour éviter les problèmes d'entrée en mode interactif
FROM python:3.14-alpine

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY ./src/ /app

ENV PYTHONUNBUFFERED=1

# Commande pour exécuter l'application
CMD ["python", "src/main.py"]

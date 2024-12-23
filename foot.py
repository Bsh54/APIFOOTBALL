import os
import requests
import json
import time
import threading
from datetime import datetime
from flask import Flask, jsonify

# Nombre de threads à utiliser pour effectuer les requêtes en parallèle
NUM_THREADS = 5

# Fonction pour récupérer les données de football
def fetch_football_data():
    try:
        # Obtenir la date du jour au format "YYYY-MM-DD"
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Construire l'URL de l'API avec la date du jour
        api_url = f"https://www.sofascore.com/api/v1/sport/football/scheduled-events/{today}"
        
        # Configuration des en-têtes pour contourner les restrictions
        headers = {
            'accept': '*/*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'en-US,en;q=0.9',
            'cache-control': 'no-cache',
            'pragma': 'no-cache',
            'user-agent': 'Mozilla/5.0 (iPad; CPU OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1'
        }

        # Envoyer une requête GET à l'API
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()  # Lever une exception en cas d'erreur HTTP
        
        # Traiter la réponse JSON
        events = response.json().get("events", [])
        
        # Trier et structurer les données
        structured_data = {
            "finished": [],
            "ongoing": [],
            "upcoming": []
        }

        for event in events:
            match = {
                "homeTeam": event.get("homeTeam", {}).get("name", "Unknown"),
                "awayTeam": event.get("awayTeam", {}).get("name", "Unknown"),
                "startTime": datetime.fromtimestamp(event.get("startTimestamp", 0)).strftime("%Y-%m-%d %H:%M:%S") if event.get("startTimestamp") else "Unknown",
                "id": event.get("id", "Unknown"),
                "seasonId": event.get("season", {}).get("id", "Unknown"),  # Récupérer l'id de la saison
                "homeScore": event.get("homeScore", {}).get("display", 0),
                "awayScore": event.get("awayScore", {}).get("display", 0),
                "status": event.get("status", {}).get("type", "Unknown"),
                "tournament": event.get("tournament", {}).get("name", "Unknown")  # Ajouter le nom du championnat ici
            }
            
            # Ajouter des heures spécifiques en fonction du statut
            if match["status"] == "finished":
                match["endTime"] = datetime.fromtimestamp(event.get("lastUpdatedTimestamp", 0)).strftime("%Y-%m-%d %H:%M:%S") if event.get("lastUpdatedTimestamp") else "Unknown"
                structured_data["finished"].append(match)
            elif match["status"] == "inprogress":
                match["currentTime"] = datetime.fromtimestamp(event.get("lastUpdatedTimestamp", 0)).strftime("%Y-%m-%d %H:%M:%S") if event.get("lastUpdatedTimestamp") else "Unknown"
                structured_data["ongoing"].append(match)
            elif match["status"] == "notstarted":
                structured_data["upcoming"].append(match)

        return structured_data

    except requests.exceptions.RequestException as e:
        print(f"Network or HTTP error occurred: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None

# Fonction pour gérer la récupération et l'écriture des données
def save_football_data():
    data = fetch_football_data()
    if data:
        # Sauvegarder les données dans un fichier JSON appelé 'foot.json'
        output_file = "foot.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Data saved to {output_file}")
    else:
        print("No data received")

# Fonction principale pour gérer la boucle et les threads
def main_loop():
    try:
        print("Starting the loop with multi-threading...")

        # Liste pour stocker les threads
        threads = []

        while True:
            # Créer et démarrer plusieurs threads pour envoyer des requêtes en parallèle
            for _ in range(NUM_THREADS):
                thread = threading.Thread(target=save_football_data)
                threads.append(thread)
                thread.start()

            # Attendre que tous les threads se terminent
            for thread in threads:
                thread.join()

            # Attendre 2 secondes avant la prochaine requête
            time.sleep(2)

    except KeyboardInterrupt:
        print("\nProcess interrupted by user. Exiting...")
    except Exception as e:
        print(f"Unexpected error in main loop: {e}")

# Lancer l'application Flask
app = Flask(__name__)

# Route principale pour vérifier si l'API fonctionne
@app.route('/')
def home():
    return "Football Data API is running!"

# Route pour obtenir les données de football
@app.route('/api/data')
def get_data():
    try:
        with open('foot.json', 'r', encoding='utf-8') as file:
            data = json.load(file)
        return jsonify(data)
    except Exception as e:
        return jsonify({"

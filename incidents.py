import json
import time
import asyncio
import aiohttp
import os
from flask import Flask, jsonify

app = Flask(__name__)

# Configuration du logger pour enregistrer les erreurs
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def decode_unicode_string(input_string):
    try:
        return input_string.encode('utf-8').decode('unicode_escape')
    except Exception as e:
        logging.error(f"Erreur de décodage de la chaîne : {e}")
        return input_string

async def get_incidents_for_match(session, match_id):
    url = f"https://www.sofascore.com/api/v1/event/{match_id}/incidents"

    try:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                incidents = []

                if 'incidents' in data:
                    for incident in data['incidents']:
                        if incident.get("isLive", False):  # Vérifier si l'incident est en direct
                            incident_type = incident.get("incidentType")
                            incident_data = {
                                "incidentId": incident.get("id"),
                                "matchId": match_id,
                                "incidentType": incident_type,
                                "time": incident.get("time"),
                                "team": "home" if incident.get("isHome", False) else "away"
                            }

                            # Ajouter des données spécifiques à chaque type d'incident
                            if incident_type == "goal":
                                incident_data.update({
                                    "player": incident.get("player", {}).get("name"),
                                    "playerId": incident.get("player", {}).get("id"),
                                    "score": {
                                        "home": incident.get("homeScore"),
                                        "away": incident.get("awayScore")
                                    }
                                })
                            elif incident_type == "card":
                                incident_data.update({
                                    "player": incident.get("player", {}).get("name"),
                                    "playerId": incident.get("player", {}).get("id"),
                                    "cardType": incident.get("cardType"),
                                    "rescinded": incident.get("rescinded", False)
                                })
                            elif incident_type == "substitution":
                                incident_data.update({
                                    "playerIn": incident.get("playerIn", {}).get("name"),
                                    "playerOut": incident.get("playerOut", {}).get("name"),
                                    "injury": incident.get("injury", False)
                                })
                            elif incident_type == "penalty":
                                incident_data.update({
                                    "player": incident.get("player", {}).get("name"),
                                    "playerId": incident.get("player", {}).get("id"),
                                    "outcome": incident.get("outcome")
                                })
                            elif incident_type == "injury":
                                incident_data.update({
                                    "player": incident.get("player", {}).get("name"),
                                    "playerId": incident.get("player", {}).get("id")
                                })
                            elif incident_type == "offside":
                                incident_data.update({
                                    "player": incident.get("player", {}).get("name"),
                                    "playerId": incident.get("player", {}).get("id")
                                })
                            elif incident_type == "var":
                                incident_data.update({
                                    "decision": incident.get("decision")
                                })
                            elif incident_type == "corner":
                                pass  # Pas d'informations spécifiques supplémentaires
                            elif incident_type == "foul":
                                incident_data.update({
                                    "player": incident.get("player", {}).get("name"),
                                    "playerId": incident.get("player", {}).get("id")
                                })
                            elif incident_type == "freeKick":
                                pass  # Pas d'informations spécifiques supplémentaires
                            elif incident_type in ["kickOff", "halfTime", "fullTime"]:
                                incident_data.update({
                                    "score": {
                                        "home": incident.get("homeScore"),
                                        "away": incident.get("awayScore")
                                    }
                                })

                            incidents.append(incident_data)

                return incidents
            else:
                logging.warning(f"Erreur lors de la récupération des incidents pour le match {match_id}. Code: {response.status}")
                return None
    except Exception as e:
        logging.error(f"Erreur lors de la requête pour récupérer les incidents du match {match_id}: {e}")
        return None

async def filter_and_save_matches():
    with open('foot.json', 'r', encoding='utf-8') as file:
        data = json.load(file)

    live_matches = []

    async with aiohttp.ClientSession() as session:

        async def filter_matches(matches):
            tasks = []
            for match in matches:
                if isinstance(match, dict) and match.get("status") == "inprogress":
                    match_id = match["id"]
                    task_incidents = get_incidents_for_match(session, match_id)
                    tasks.append(task_incidents)

            results = await asyncio.gather(*tasks, return_exceptions=True)

            for idx, match in enumerate(matches):
                if isinstance(match, dict) and match.get("status") == "inprogress":
                    incidents_result = results[idx]

                    if isinstance(incidents_result, list):
                        match_data = {
                            "homeTeam": decode_unicode_string(match["homeTeam"]),
                            "awayTeam": decode_unicode_string(match["awayTeam"]),
                            "id": match["id"],
                            "incidents": incidents_result
                        }
                        live_matches.append(match_data)

        if isinstance(data, list):
            await filter_matches(data)

        if "ongoing" in data:
            await filter_matches(data["ongoing"])

    if live_matches:
        with open('evenements.json', 'w', encoding='utf-8') as file:
            json.dump(live_matches, file, ensure_ascii=False, indent=4)
        logging.info("Les matchs en cours avec leurs incidents ont été enregistrés dans evenements.json.")
    else:
        logging.warning("Aucun match en cours n'a été trouvé.")

async def main():
    while True:
        await filter_and_save_matches()
        await asyncio.sleep(1)

@app.route('/')
def home():
    return "Football Data API is running!"

@app.route('/api/data')
def get_data():
    # Charger les données du fichier JSON
    with open('evenements.json', 'r', encoding='utf-8') as file:
        data = json.load(file)
    return jsonify(data)

if __name__ == "__main__":
    # Obtenir le port à partir de la variable d'environnement ou utiliser 5000 par défaut
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

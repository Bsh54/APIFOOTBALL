import json
import time
import asyncio
import aiohttp
import os

# Fonction pour convertir une cote fractionnelle en décimale
def fractional_to_decimal(fractional_value):
    try:
        numerator, denominator = map(int, fractional_value.split('/'))
        return (numerator / denominator) + 1
    except Exception as e:
        print(f"Erreur de conversion de la cote {fractional_value}: {e}")
        return None

# Fonction pour décoder les chaînes contenant des séquences Unicode échappées
def decode_unicode_string(input_string):
    try:
        # Utilise decode('unicode_escape') pour s'assurer que les caractères sont correctement affichés
        return input_string.encode('utf-8').decode('unicode_escape')
    except Exception as e:
        print(f"Erreur de décodage de la chaîne : {e}")
        return input_string

# Fonction asynchrone pour récupérer les cotes d'un match via l'API
async def get_odds_for_match(session, match_id):
    url = f"https://www.sofascore.com/api/v1/event/{match_id}/odds/1/featured"
    
    try:
        async with session.get(url) as response:
            # Vérifie si la requête a réussi (code 200)
            if response.status == 200:
                data = await response.json()
                odds = {}

                # Extraire les cotes 1, X, 2 à partir de la réponse JSON
                if 'featured' in data:
                    featured_data = data['featured']
                    if 'default' in featured_data:
                        choices = featured_data['default']['choices']
                        for choice in choices:
                            if choice['name'] == '1':
                                odds['1'] = fractional_to_decimal(choice['fractionalValue'])
                            elif choice['name'] == 'X':
                                odds['X'] = fractional_to_decimal(choice['fractionalValue'])
                            elif choice['name'] == '2':
                                odds['2'] = fractional_to_decimal(choice['fractionalValue'])
                
                return odds
            else:
                print(f"Erreur lors de la récupération des données pour le match {match_id}. Code: {response.status}")
                return None
    except Exception as e:
        print(f"Erreur lors de la requête pour le match {match_id}: {e}")
        return None

# Fonction pour filtrer et sauvegarder les matchs avec leurs cotes de manière asynchrone
async def filter_and_save_matches():
    with open('foot.json', 'r', encoding='utf-8') as file:
        data = json.load(file)

    inprogress_matches = []
    notstarted_matches = []

    # Crée une session aiohttp pour faire les appels asynchrones
    async with aiohttp.ClientSession() as session:

        # Fonction pour filtrer les matchs et récupérer leurs cotes
        async def filter_matches(matches, status):
            tasks = []
            for match in matches:
                if isinstance(match, dict):
                    if match.get("status") == status:
                        match_id = match["id"]
                        task = get_odds_for_match(session, match_id)
                        tasks.append(task)
            
            # Attendre que toutes les tâches asynchrones soient terminées
            results = await asyncio.gather(*tasks)
            
            # Organiser les résultats
            for idx, match in enumerate(matches):
                if isinstance(match, dict) and match.get("status") == status and results[idx]:
                    match_data = {
                        "homeTeam": decode_unicode_string(match["homeTeam"]),
                        "awayTeam": decode_unicode_string(match["awayTeam"]),
                        "id": match["id"],
                        "odds": results[idx]
                    }
                    if status == "inprogress":
                        inprogress_matches.append(match_data)
                    elif status == "notstarted":
                        notstarted_matches.append(match_data)

        # Filtrer les matchs dans la racine
        if isinstance(data, list):
            await filter_matches(data, "inprogress")
            await filter_matches(data, "notstarted")

        # Filtrer les matchs dans "ongoing"
        if "ongoing" in data:
            await filter_matches(data["ongoing"], "inprogress")

        # Filtrer les matchs dans "upcoming"
        if "upcoming" in data:
            await filter_matches(data["upcoming"], "notstarted")

    # Enregistrer les résultats dans scores.json si des matchs ont été filtrés
    if inprogress_matches or notstarted_matches:
        with open('scores.json', 'w', encoding='utf-8') as file:
            json.dump({
                "inprogress": inprogress_matches,
                "notstarted": notstarted_matches
            }, file, ensure_ascii=False, indent=4)  # `ensure_ascii=False` permet de conserver les caractères spéciaux
        print("Les matchs avec leurs cotes ont été enregistrés dans scores.json.")
    else:
        print("Aucun match correspondant n'a été trouvé.")

# Fonction principale pour exécuter la boucle asynchrone
async def main():
    while True:
        await filter_and_save_matches()
        await asyncio.sleep(1)  # Pause de 1 seconde avant la prochaine itération pour limiter la fréquence des appels

if __name__ == "__main__":
    # Obtenir le port à partir de la variable d'environnement ou utiliser 5000 par défaut
    port = int(os.environ.get("PORT", 5000))
    import flask
    from flask import Flask

    # Créer une instance Flask
    app = Flask(__name__)

    # Définir une route pour vérifier si l'API fonctionne
    @app.route('/')
    def home():
        return "Football Data API is running!"

    # Définir une route pour obtenir les données des matchs
    @app.route('/api/data')
    def get_data():
        # Charger les données du fichier JSON
        with open('scores.json', 'r', encoding='utf-8') as file:
            data = json.load(file)
        return flask.jsonify(data)

    # Lancer le serveur Flask sur le port dynamique
    app.run(host="0.0.0.0", port=port)
    
    # Exécuter la boucle asynchrone pour récupérer et sauvegarder les matchs
    asyncio.run(main())

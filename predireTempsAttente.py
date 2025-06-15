# predireTempsAttente.py

import requests
from bs4 import BeautifulSoup
import json
import re
from functools import lru_cache
from datetime import datetime # Uniquement pour un exemple d'utilisation
import numpy as np 
import matplotlib.pyplot as plt

# --- Configuration Globale ---
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
})

RE_MONTH_CHART = re.compile(r'\[\{"name":".*?","data":(.*?)}\]', re.DOTALL)

URLS = {
    'Blue Fire': 'https://queue-times.com/fr/parks/51/rides/5603',
    'Voltron Nevera': 'https://queue-times.com/fr/parks/51/rides/13349',
    'Wodan': 'https://queue-times.com/fr/parks/51/rides/5602',
    'Euro-Mir': 'https://queue-times.com/fr/parks/51/rides/5605',
    'Voletarium': 'https://queue-times.com/fr/parks/51/rides/5630',
    'Pirates in Batavia': 'https://queue-times.com/fr/parks/51/rides/5617',
    'Silver Star': 'https://queue-times.com/fr/parks/51/rides/5604',
    'Arthur': 'https://queue-times.com/fr/parks/51/rides/5618',
    'Matterhorn-Blitz': 'https://queue-times.com/fr/parks/51/rides/5607',
    'Eurosat': 'https://queue-times.com/fr/parks/51/rides/5737',
    'Poseidon': 'https://queue-times.com/fr/parks/51/rides/5611'
}

@lru_cache(maxsize=None)
def fetch_page_content(url: str) -> str:
    """
    Récupère le contenu HTML d'une URL en utilisant une session partagée.
    Met en cache les résultats pour éviter des requêtes répétées à la même URL.
    """
    try:
        resp = session.get(url, timeout=10)
        resp.raise_for_status()
        return resp.text
    except requests.exceptions.RequestException as e:
        print(f"Erreur de requête pour {url}: {e}")
        return ""

@lru_cache(maxsize=128)
def predire_temps_attente(attraction: str, heure_cible: int, semaine_cible_num: int, jour_cible: str) -> float:
    """
    Prédit le temps d'attente pour une attraction à une heure et une semaine cibles.
    Les semaines 3 à 10 (incluses) sont considérées comme exclues.

    Args:
        attraction (str): Le nom de l'attraction.
        heure_cible (int): L'heure pour laquelle prédire (ex: 10 pour 10h00).
        semaine_cible_num (int): Le numéro de la semaine cible (0-52).
        jour_cible (str): Le jour de la semaine cible (ex: 'lun', 'mar', 'sam').

    Returns:
        float: Le temps d'attente prédit en minutes. Retourne 0.0 si la semaine est exclue ou en cas d'erreur.
    """
    # Vérification des semaines exclues
    if 3 <= semaine_cible_num <= 10:
        print(f"Avertissement: La semaine {semaine_cible_num} est exclue. Prédiction non effectuée.")
        return 0.0

    url = URLS.get(attraction)
    if not url:
        print(f"Avertissement: URL non trouvée pour l'attraction '{attraction}'.")
        return 0.0

    html_content = fetch_page_content(url)
    if not html_content:
        print(f"Avertissement: Impossible de récupérer le contenu de la page pour {attraction}.")
        return 0.0
        
    soup = BeautifulSoup(html_content, 'html.parser')

    weekly_averages_map = {}
    hourly_pattern_map = {}
    weekly_pattern_map = {}

    # --- Extraction des données de moyenne par semaine (chart-6) ---
    script_chart6_tag = soup.find('script', string=lambda t: t and 'chart-6' in t)
    if script_chart6_tag and script_chart6_tag.string:
        match_chart6 = RE_MONTH_CHART.search(script_chart6_tag.string)
        if match_chart6:
            weekly_data_str = match_chart6.group(1)
            weekly_raw_data = json.loads(f'[{{"data":{weekly_data_str}}}]')[0]["data"]
            weekly_averages_map = {
                int(entry[0]): float(entry[1]) 
                for entry in weekly_raw_data 
                if isinstance(entry, list) and len(entry) == 2 and entry[1] is not None
            }
    else:
        print(f"Avertissement: Script chart-6 non trouvé ou vide pour {attraction}.")

    # --- Extraction des données horaires (chart-5) ---
    script_chart5_tag = soup.find('script', string=lambda t: t and 'chart-5' in t)
    if script_chart5_tag and script_chart5_tag.string:
        match_chart5 = RE_MONTH_CHART.search(script_chart5_tag.string)
        if match_chart5:
            hourly_data_str = match_chart5.group(1)
            hourly_raw_data = json.loads(f'[{{"data":{hourly_data_str}}}]')[0]["data"]
            hourly_pattern_map = {
                int(entry[0]): float(entry[1]) 
                for entry in hourly_raw_data 
                if isinstance(entry, list) and len(entry) == 2 and entry[1] is not None
            }
    else:
        print(f"Avertissement: Script chart-5 non trouvé ou vide pour {attraction}.")
    
    # --- Extraction des données journalières de la semaine (chart-4) ---
    script_chart4_tag = soup.find('script', string=lambda t: t and 'chart-4' in t)
    if script_chart4_tag and script_chart4_tag.string:
        match_chart4 = RE_MONTH_CHART.search(script_chart4_tag.string)
        if match_chart4:
            weekly_data_str = match_chart4.group(1)
            weekly_raw_data = json.loads(f'[{{"data":{weekly_data_str}}}]')[0]["data"]
            weekly_pattern_map = {
                entry[0]: float(entry[1]) 
                for entry in weekly_raw_data 
                if isinstance(entry, list) and len(entry) == 2 and entry[1] is not None
            }
    else:
        print(f"Avertissement: Script chart-4 non trouvé ou vide pour {attraction}.")
        
    # --- Début de la logique de calcul ---

    # 1. Obtenir le temps d'attente de base pour la semaine cible.
    if not weekly_averages_map:
        print(f"Erreur: Données de moyenne hebdomadaire indisponibles pour {attraction}. Impossible de prédire.")
        return 0.0

    baseline_wait = weekly_averages_map.get(semaine_cible_num)
    if baseline_wait is None:
        if weekly_averages_map.values():
            baseline_wait = sum(weekly_averages_map.values()) / len(weekly_averages_map)
            print(f"Info: Semaine {semaine_cible_num} non trouvée. Utilisation de la moyenne générale ({baseline_wait:.1f} min).")
        else:
            return 0.0 # Ne devrait pas arriver si le premier 'if' est passé, mais par sécurité.

    # 2. Calculer le multiplicateur journalier pour ajuster en fonction du jour de la semaine.
    daily_multiplier = 1.0
    if weekly_pattern_map and weekly_pattern_map.values():
        avg_daily_wait = sum(weekly_pattern_map.values()) / len(weekly_pattern_map)
        jour_cible_key = jour_cible.lower() # Les clés sont du type 'lun.', 'mar.', etc.
        
        if avg_daily_wait > 0:
            day_specific_wait = weekly_pattern_map.get(jour_cible_key)
            if day_specific_wait is not None:
                daily_multiplier = day_specific_wait / avg_daily_wait
            else:
                print(f"Avertissement: Jour '{jour_cible_key}' non trouvé. Le multiplicateur journalier ne sera pas appliqué.")
    
    # 3. Calculer le multiplicateur horaire pour ajuster en fonction de l'heure de la journée.
    hourly_multiplier = 1.0
    if hourly_pattern_map and hourly_pattern_map.values():
        avg_hourly_wait = sum(hourly_pattern_map.values()) / len(hourly_pattern_map)
        
        if avg_hourly_wait > 0:
            hour_specific_wait = hourly_pattern_map.get(heure_cible)
            if hour_specific_wait is not None:
                hourly_multiplier = hour_specific_wait / avg_hourly_wait
            else:
                print(f"Avertissement: Heure '{heure_cible}h' non trouvée. Le multiplicateur horaire ne sera pas appliqué.")

    # 4. Calcul final de la prédiction.
    predicted_wait = baseline_wait * daily_multiplier * hourly_multiplier
    
    return round(predicted_wait, 1)
"""
# --- Exemple d'utilisation ---
if __name__ == "__main__":
    # Test avec une attraction, heure, semaine et jour spécifiques
    listHeure = np.linspace(9, 19, 11)
    tempsAttente = []
    for heure in listHeure:
        tempsAttente.append(predire_temps_attente(
            attraction='Blue Fire', 
            heure_cible=heure,            # 14h00
            semaine_cible_num=22,      # Semaine 30 (pleine saison estivale)
            jour_cible='dim'           # Un Samedi
        ))
    plt.figure()
    plt.plot(listHeure, tempsAttente)
    plt.grid()
    plt.show()
    #print(f"  -> Temps d'attente prédit pour Blue Fire (Samedi, 9h, Semaine 24): {prediction_voltron} minutes")
    #print("-" * 35)
"""

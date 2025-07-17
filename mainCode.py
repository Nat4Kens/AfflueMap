# mainCode.py (Moteur de calcul)

import re
import requests
import json
from collections import defaultdict
from functools import lru_cache
from bs4 import BeautifulSoup
# --- CONFIGURATION ET CONSTANTES ---

ATTRACTIONS_MASTER_LIST = [
    'Wodan', 'Blue Fire', 'Voletarium', 'Voltron Nevera', 'Euro-Mir',
    'Pirates in Batavia', 'Silver Star', 'Arthur', 'Matterhorn-Blitz', 'Eurosat',
    'Poseidon', 'Castello dei Medici', 'Pegasus', 'Swiss Bob Run',
    'Atlantica SuperSplash', 'Alpine Express', 'Atlantis Adventure'
]

URLS = {
    'Blue Fire': 'https://queue-times.com/fr/parks/51/rides/5603', 'Voltron Nevera': 'https://queue-times.com/fr/parks/51/rides/13349',
    'Wodan': 'https://queue-times.com/fr/parks/51/rides/5602', 'Euro-Mir': 'https://queue-times.com/fr/parks/51/rides/5605',
    'Voletarium': 'https://queue-times.com/fr/parks/51/rides/5630', 'Pirates in Batavia': 'https://queue-times.com/fr/parks/51/rides/5617',
    'Silver Star': 'https://queue-times.com/fr/parks/51/rides/5604', 'Arthur': 'https://queue-times.com/fr/parks/51/rides/5618',
    'Matterhorn-Blitz': 'https://queue-times.com/fr/parks/51/rides/5607', 'Eurosat': 'https://queue-times.com/fr/parks/51/rides/5737',
    'Poseidon': 'https://queue-times.com/fr/parks/51/rides/5611', 'Castello dei Medici': 'https://queue-times.com/fr/parks/51/rides/5616',
    'Pegasus': 'https://queue-times.com/fr/parks/51/rides/5608', 'Swiss Bob Run': 'https://queue-times.com/fr/parks/51/rides/5613',
    'Atlantis Adventure': 'https://queue-times.com/fr/parks/51/rides/5615', 'Atlantica SuperSplash': 'https://queue-times.com/fr/parks/51/rides/5610',
    'Alpine Express': 'https://queue-times.com/fr/parks/51/rides/5606'
}

COMPLETE_EDGES_UNPONDERED = [
    ('Blue Fire', 'Voltron Nevera', 15), ('Blue Fire', 'Wodan', 3), ('Blue Fire', 'Euro-Mir', 11), ('Blue Fire', 'Voletarium', 28),
    ('Voltron Nevera', 'Wodan', 9), ('Voltron Nevera', 'Euro-Mir', 1), ('Euro-Mir', 'Wodan', 8), ('Voletarium', 'Voltron Nevera', 8),
    ('Voletarium', 'Wodan', 16), ('Voletarium', 'Euro-Mir', 9), ('Pirates in Batavia', 'Blue Fire', 7), ('Pirates in Batavia', 'Voltron Nevera', 9),
    ('Pirates in Batavia', 'Wodan', 10), ('Pirates in Batavia', 'Euro-Mir', 4), ('Pirates in Batavia', 'Voletarium', 18), ('Pirates in Batavia', 'Silver Star', 12),
    ('Pirates in Batavia', 'Arthur', 8), ('Pirates in Batavia', 'Matterhorn-Blitz', 9), ('Pirates in Batavia', 'Eurosat', 11), ('Pirates in Batavia', 'Poseidon', 13),
    ('Silver Star', 'Blue Fire', 19), ('Silver Star', 'Voltron Nevera', 6), ('Silver Star', 'Wodan', 21), ('Silver Star', 'Euro-Mir', 7),
    ('Silver Star', 'Voletarium', 9), ('Silver Star', 'Arthur', 13), ('Silver Star', 'Matterhorn-Blitz', 3), ('Silver Star', 'Eurosat', 2),
    ('Silver Star', 'Poseidon', 2), ('Arthur', 'Blue Fire', 13), ('Arthur', 'Voltron Nevera', 10), ('Arthur', 'Wodan', 13),
    ('Arthur', 'Euro-Mir', 8), ('Arthur', 'Voletarium', 19), ('Arthur', 'Matterhorn-Blitz', 10), ('Arthur', 'Eurosat', 12),
    ('Arthur', 'Poseidon', 14), ('Matterhorn-Blitz', 'Blue Fire', 16), ('Matterhorn-Blitz', 'Voltron Nevera', 3), ('Matterhorn-Blitz', 'Wodan', 18),
    ('Matterhorn-Blitz', 'Euro-Mir', 4), ('Matterhorn-Blitz', 'Voletarium', 11), ('Matterhorn-Blitz', 'Eurosat', 2), ('Matterhorn-Blitz', 'Poseidon', 5),
    ('Eurosat', 'Blue Fire', 18), ('Eurosat', 'Voltron Nevera', 5), ('Eurosat', 'Wodan', 20), ('Eurosat', 'Euro-Mir', 6),
    ('Eurosat', 'Voletarium', 9), ('Eurosat', 'Poseidon', 4), ('Poseidon', 'Blue Fire', 19), ('Poseidon', 'Voltron Nevera', 2),
    ('Poseidon', 'Wodan', 19), ('Poseidon', 'Euro-Mir', 5), ('Poseidon', 'Voletarium', 14), ('Entree', 'Blue Fire', 27),
    ('Entree', 'Voltron Nevera', 13), ('Entree', 'Wodan', 27), ('Entree', 'Euro-Mir', 14), ('Entree', 'Voletarium', 1),
    ('Entree', 'Pirates in Batavia', 20), ('Entree', 'Silver Star', 7), ('Entree', 'Arthur', 18), ('Entree', 'Matterhorn-Blitz', 8),
    ('Entree', 'Eurosat', 8), ('Entree', 'Poseidon', 11), ('Entree', 'Swiss Bob Run', 11), ('Entree', 'Atlantis Adventure', 12), ('Entree', 'Atlantica SuperSplash', 23),
    ('Entree', 'Alpine Express', 20),
    ('Castello dei Medici', 'Entree', 4), ('Castello dei Medici', 'Poseidon', 6), ('Castello dei Medici', 'Eurosat', 3), ('Castello dei Medici', 'Matterhorn-Blitz', 5),
    ('Castello dei Medici', 'Arthur', 12), ('Castello dei Medici', 'Silver Star', 3), ('Castello dei Medici', 'Pirates in Batavia', 12), ('Castello dei Medici', 'Voletarium', 6),
    ('Castello dei Medici', 'Euro-Mir', 8), ('Castello dei Medici', 'Wodan', 22), ('Castello dei Medici', 'Voltron Nevera', 8), ('Castello dei Medici', 'Blue Fire', 19),
    ('Pegasus', 'Entree', 10), ('Pegasus', 'Poseidon', 1), ('Pegasus', 'Eurosat', 4), ('Pegasus', 'Matterhorn-Blitz', 5),
    ('Pegasus', 'Arthur', 14), ('Pegasus', 'Silver Star', 2), ('Pegasus', 'Pirates in Batavia', 13), ('Pegasus', 'Voletarium', 11),
    ('Pegasus', 'Euro-Mir', 9), ('Pegasus', 'Wodan', 22), ('Pegasus', 'Voltron Nevera', 7), ('Pegasus', 'Blue Fire', 20), ('Pegasus', 'Castello dei Medici', 5),
    ('Swiss Bob Run', 'Poseidon', 6), ('Swiss Bob Run', 'Eurosat', 3), ('Swiss Bob Run', 'Matterhorn-Blitz', 1), ('Swiss Bob Run', 'Pegasus', 6),
    ('Swiss Bob Run', 'Arthur', 9), ('Swiss Bob Run', 'Silver Star', 4), ('Swiss Bob Run', 'Pirates in Batavia', 8), ('Swiss Bob Run', 'Voletarium', 12),
    ('Swiss Bob Run', 'Euro-Mir', 4), ('Swiss Bob Run', 'Wodan', 18), ('Swiss Bob Run', 'Voltron Nevera', 4), ('Swiss Bob Run', 'Blue Fire', 15), ('Swiss Bob Run', 'Castello dei Medici', 6),
    ('Atlantis Adventure', 'Poseidon', 5), ('Atlantis Adventure', 'Eurosat', 3), ('Atlantis Adventure', 'Matterhorn-Blitz', 1), ('Atlantis Adventure', 'Pegasus', 6),
    ('Atlantis Adventure', 'Arthur', 8), ('Atlantis Adventure', 'Silver Star', 5), ('Atlantis Adventure', 'Pirates in Batavia', 7), ('Atlantis Adventure', 'Voletarium', 13),
    ('Atlantis Adventure', 'Euro-Mir', 3), ('Atlantis Adventure', 'Wodan', 17), ('Atlantis Adventure', 'Voltron Nevera', 1), ('Atlantis Adventure', 'Blue Fire', 14), ('Atlantis Adventure', 'Castello dei Medici', 6),
    ('Atlantis Adventure', 'Swiss Bob Run', 3),
    ('Atlantica SuperSplash', 'Poseidon', 19), ('Atlantica SuperSplash', 'Eurosat', 17), ('Atlantica SuperSplash', 'Matterhorn-Blitz', 15), ('Atlantica SuperSplash', 'Pegasus', 19),
    ('Atlantica SuperSplash', 'Arthur', 9), ('Atlantica SuperSplash', 'Silver Star', 18), ('Atlantica SuperSplash', 'Pirates in Batavia', 7), ('Atlantica SuperSplash', 'Voletarium', 24),
    ('Atlantica SuperSplash', 'Euro-Mir', 10), ('Atlantica SuperSplash', 'Wodan', 6), ('Atlantica SuperSplash', 'Voltron Nevera', 15), ('Atlantica SuperSplash', 'Blue Fire', 6), ('Atlantica SuperSplash', 'Castello dei Medici', 18),
    ('Atlantica SuperSplash', 'Swiss Bob Run', 14), ('Atlantica SuperSplash', 'Atlantis Adventure', 13),
    ('Alpine Express', 'Poseidon', 18), ('Alpine Express', 'Eurosat', 16), ('Alpine Express', 'Matterhorn-Blitz', 14), ('Alpine Express', 'Pegasus', 18),
    ('Alpine Express', 'Arthur', 5), ('Alpine Express', 'Silver Star', 17), ('Alpine Express', 'Pirates in Batavia', 6), ('Alpine Express', 'Voletarium', 23),
    ('Alpine Express', 'Euro-Mir', 9), ('Alpine Express', 'Wodan', 11), ('Alpine Express', 'Voltron Nevera', 14), ('Alpine Express', 'Blue Fire', 11), ('Alpine Express', 'Castello dei Medici', 17),
    ('Alpine Express', 'Swiss Bob Run', 13), ('Alpine Express', 'Atlantica SuperSplash', 7), ('Alpine Express', 'Atlantis Adventure', 12)
]

ATTRACTIONS_COORDS = {
    'Entree': (48.26886239084585, 7.7218611694409045), 'Voletarium': (48.26917304513733, 7.722443208799992),
    'Eurosat': (48.267451577912816, 7.72113123949057), 'Silver Star': (48.26779998024085, 7.720126590003773),
    'Euro-Mir': (48.26507602609998, 7.720178628240745), 'Wodan': (48.26138819760847, 7.7192129584382885),
    'Blue Fire': (48.26265872340149, 7.718827721822693), 'Voltron Nevera': (48.2657797944176, 7.719762395202016),
    'Pirates in Batavia': (48.26358868421831, 7.7204499731581135), 'Arthur': (48.26389057631639, 7.723843203049346),
    'Matterhorn-Blitz': (48.26691168136572, 7.72049900063425), 'Poseidon': (48.26666361205288, 7.719339791552477),
    'Castello dei Medici': (48.26778972322049, 7.7219478107095005), 'Pegasus': (48.267802325534184, 7.719292403563365),
    'Swiss Bob Run' : (48.26641724603062, 7.721222909834505), 'Atlantica SuperSplash' : (48.26206292443042, 7.721499320393662),
    'Alpine Express' : (48.2621812175191, 7.722749967431886), 'Atlantis Adventure': (48.26622780789098, 7.7202422772430905)
}

# --- FONCTIONS DE CALCUL ---

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
})

RE_CHART_SCRIPT = re.compile(r"var createChart = function")
RE_JSON_DATA = re.compile(r"\[\{\"name\":.*?\}\]", re.DOTALL)
RE_MONTH_CHART = re.compile(r'\[\{"name":".*?","data":(.*?)}\]', re.DOTALL)

@lru_cache(maxsize=None)
def fetch_page_content(url: str) -> str:
    """Fetches the content of a URL and caches the result."""
    try:
        resp = session.get(url, timeout=10)
        resp.raise_for_status()
        return resp.text
    except requests.exceptions.RequestException as e:
        print(f"Erreur de réseau en contactant {url}: {e}")
        return ""

def get_actual_wait_time(attraction: str) -> float:
    """Gets the last reported wait time for an attraction."""
    url = URLS.get(attraction)
    if not url: return 0.0
    html = fetch_page_content(url)
    if not html: return 0.0
    soup = BeautifulSoup(html, 'html.parser')
    script = soup.find('script', string=RE_CHART_SCRIPT)
    if not script: return 0.0
    match = RE_JSON_DATA.search(script.string)
    if not match: return 0.0
    try:
        data = json.loads(match.group())
        for series in data:
            if series['name'] == 'Signalé par le parc' and series['data']:
                return float(series['data'][-1][1])
    except (json.JSONDecodeError, IndexError):
        return 0.0
    return 0.0

def get_predicted_wait_time(attraction: str, target_hour: int) -> float:
    """Predicts wait time for a given hour based on historical data."""
    if not (9 <= target_hour <= 20): return 0.0
    url = URLS.get(attraction)
    if not url: return 0.0
    html_content = fetch_page_content(url)
    if not html_content: return 0.0
    soup = BeautifulSoup(html_content, 'html.parser')
    script_chart5_tag = soup.find('script', string=lambda t: t and 'chart-5' in t)
    if script_chart5_tag and script_chart5_tag.string:
        match_chart5 = RE_MONTH_CHART.search(script_chart5_tag.string)
        if match_chart5:
            try:
                hourly_raw_data = json.loads(f'[{{"data":{match_chart5.group(1)}}}]')[0]["data"]
                hourly_pattern_map = {int(e[0]): float(e[1]) for e in hourly_raw_data if e[1] is not None}
                return hourly_pattern_map.get(target_hour, 0.0)
            except (json.JSONDecodeError, IndexError):
                return 0.0
    return 0.0

def calculer_facteur_opportunite(actual_wait, avg_wait):
    """
    Calcule un facteur d'opportunité en utilisant une loi de puissance
    avec des exposants différents pour la récompense et la pénalité.
    """
    # --- Constantes de la stratégie ---
    # Exposant pour la récompense. > 1 rend la récompense plus forte.
    P_RECOMPENSE = 2
    # Exposant pour la pénalité. > 1 rend la pénalité plus forte.
    P_PENALITE = 3 
    
    # --- Sécurité et cas par défaut ---
    if avg_wait is None or actual_wait is None or avg_wait <= 5:
        return 1.0

    # Le ratio est la base de notre calcul
    ratio = actual_wait / avg_wait
    
    # --- Logique de puissance double ---
    if ratio <= 1:
        # Cas Récompense : on applique la puissance de récompense
        facteur = ratio ** P_RECOMPENSE
    else:
        # Cas Pénalité : on applique la puissance de pénalité
        facteur = ratio ** P_PENALITE
    
    # --- Plafonnement (clamping) ---
    return max(0.1, min(facteur, 5.0))

def find_best_next_step(current_location, attractions_to_visit, current_time):
    """
    Analyse les attractions en utilisant un coût où le temps de marche est fixe
    et seul le temps d'attente est pondéré par le facteur d'opportunité.
    """
    travel_times = defaultdict(lambda: float('inf'))
    for loc1, loc2, weight in COMPLETE_EDGES_UNPONDERED:
        travel_times[(loc1, loc2)] = weight
        travel_times[(loc2, loc1)] = weight

    all_candidates_details = []
    best_choice_details = None
    lowest_cost = float('inf')

    for candidate in attractions_to_visit:
        if candidate == current_location:
            continue
        
        travel_time = travel_times.get((current_location, candidate), 30)
        real_current_wait = get_actual_wait_time(candidate)
        predicted_wait_now = get_predicted_wait_time(
            attraction=candidate, target_hour=current_time.hour
        )
                
        facteur_opportunite = calculer_facteur_opportunite(
            actual_wait=real_current_wait,
            avg_wait=predicted_wait_now
        )
        
        wait_time_pondered = real_current_wait * facteur_opportunite
        
        final_cost = travel_time + wait_time_pondered

        candidate_details = {
            "destination": candidate,
            "travel_time": travel_time,
            "real_wait_time": real_current_wait,
            "predicted_wait_time": predicted_wait_now,
            "cost": final_cost
        }
        all_candidates_details.append(candidate_details)

        if final_cost < lowest_cost:
            lowest_cost = final_cost
            best_choice_details = candidate_details
            
    return best_choice_details, all_candidates_details

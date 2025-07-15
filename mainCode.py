import re
import json
import requests
from collections import defaultdict
import numpy as np
from bs4 import BeautifulSoup

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
    'Poseidon': 'https://queue-times.com/fr/parks/51/rides/5611',
    'Castello dei Medici': 'https://queue-times.com/fr/parks/51/rides/5616',
    'Pegasus': 'https://queue-times.com/fr/parks/51/rides/5608',
    'Swiss Bob Run': 'https://queue-times.com/fr/parks/51/rides/5613',
    'Atlantis Adventure': 'https://queue-times.com/fr/parks/51/rides/5615',
    'Atlantica SuperSplash': 'https://queue-times.com/fr/parks/51/rides/5610',
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
    ('Entree', 'Alpine Express', 20)
]

travel_times_from_to = defaultdict(lambda: float('inf'))
for loc1, loc2, weight in COMPLETE_EDGES_UNPONDERED:
    travel_times_from_to[(loc1, loc2)] = weight
    travel_times_from_to[(loc2, loc1)] = weight

RE_CHART_SCRIPT = re.compile(r"var createChart = function")
RE_JSON_DATA = re.compile(r'\[{"name":.*?}\]', re.DOTALL)

dernierTemps = None
session = None

def login_and_get_session(username, password):
    global session
    if session:
        return session

    LOGIN_URL = 'https://queue-times.com/fr/users/sign_in'
    local_session = requests.Session()
    try:
        login_page = local_session.get(LOGIN_URL, timeout=10)
        login_page.raise_for_status()
        soup = BeautifulSoup(login_page.text, 'html.parser')
        token_element = soup.find('input', {'name': 'authenticity_token'})
        if not token_element:
            raise ValueError("Jeton d'authenticité non trouvé.")
        token = token_element.get('value')
    except (requests.RequestException, ValueError) as e:
        print(f"Erreur lors de la récupération du jeton de sécurité : {e}")
        return None

    login_data = {
        'authenticity_token': token,
        'user[email]': username,
        'user[password]': password,
        'commit': 'Se connecter'
    }
    response = local_session.post(LOGIN_URL, data=login_data)

    if response.ok and "Déconnexion" in response.text:
        print("Connexion réussie !")
        session = local_session
        return session
    else:
        print("Échec de la connexion. Vérifiez vos identifiants.")
        return None

def fetch_page_content(url):
    try:
        resp = session.get(url, timeout=10)
        resp.raise_for_status()
        return resp.text
    except requests.exceptions.RequestException as e:
        print(f"Erreur de réseau en contactant {url}: {e}")
        return ""

def get_wait_time_ponderation_coefficient(avg_wait, actual_wait):
    """
    Calcule un coefficient qui représente la 'qualité' de l'opportunité.
    Cette fonction utilise la stratégie optimisée "Gain Mixte".
    Elle se base sur le ratio (gain relatif) et y ajoute un bonus
    proportionnel au nombre de minutes réelles économisées (gain absolu).
    """
    if avg_wait is None or actual_wait is None or avg_wait <= 5:
        return 1.0

    diff_wait = avg_wait - actual_wait

    if diff_wait <= 0:  # Le temps est pire que la moyenne -> Pénalité
        return 1 + (-diff_wait / 60)**2
    else:  # Bonne opportunité -> Récompense
        # Récompense de base sur le ratio
        base_reward = actual_wait / avg_wait
        
        # Bonus supplémentaire basé sur le gain absolu de temps (normalisé)
        absolute_gain_bonus = diff_wait / 60.0
        
        # Le nouveau coefficient est le ratio de base, auquel on soustrait le bonus.
        # Plus on gagne de minutes, plus le coefficient baisse.
        final_coefficient = base_reward - absolute_gain_bonus
        
        return max(0.01, final_coefficient) # On s'assure de ne pas avoir un coût négatif


def find_best_next_step(current_location, attractions_to_visit, travel_times_edges, current_time, verbose=False):
    best_choice_score = float('inf')
    best_choice_details = None

    for attraction_name in attractions_to_visit:
        travel_time = travel_times_edges.get((current_location, attraction_name), float('inf'))
        if travel_time == float('inf'):
            continue

        actual_wait = dernierTemps(attraction_name)
        avg_wait = 30 + 25 * np.sin((current_time.hour - 9) * np.pi / 8)

        penalty_coefficient = get_wait_time_ponderation_coefficient(avg_wait, actual_wait)
        total_cost = travel_time * penalty_coefficient

        if total_cost < best_choice_score:
            best_choice_score = total_cost
            best_choice_details = {
                "destination": attraction_name,
                "travel_time": travel_time,
                "current_wait": actual_wait,
                "score": total_cost,
                "avg_wait": avg_wait,
            }
    
    if verbose and best_choice_details:
        print(f"Meilleur choix : {best_choice_details['destination']} (Score: {best_choice_details['score']:.2f}, "
              f"Attente: {best_choice_details['current_wait']}min, Trajet: {best_choice_details['travel_time']}min)")

    return best_choice_details
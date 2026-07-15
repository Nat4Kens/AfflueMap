# mainCode.py (Moteur de calcul - Version API + CSV Large + Traduction)
import requests
import json
import csv
import os
import time 
from collections import defaultdict
from datetime import datetime, timedelta

# --- CONFIGURATION ET CONSTANTES ---
ATTRACTION_RIDE_TIME = 5 
API_URL = 'https://queue-times.com/parks/51/queue_times.json'
HISTORICAL_DATA_FILE = 'historical_hourly_waits.csv'

# Noms internes utilisés partout dans le code (graphes, CSV, etc.)
ATTRACTIONS_MASTER_LIST = [
    'Wodan', 'Blue Fire', 'Voletarium', 'Voltron Nevera', 'Euro-Mir',
    'Pirates in Batavia', 'Silver Star', 'Arthur', 'Matterhorn-Blitz', 'Eurosat',
    'Poseidon', 'Castello dei Medici', 'Pegasus', 'Swiss Bob Run',
    'Atlantica SuperSplash', 'Alpine Express', 'Atlantis Adventure'
]

# Liste des attractions éligibles à la Virtual Line
VIRTUAL_LINE_ATTRACTIONS = [
    'Blue Fire', 'Euro-Mir', 'Pirates in Batavia', 'Poseidon', 
    'Voletarium', 'Voltron Nevera', 'Wodan'
]

# ==============================================================================
#  AJOUT DU DICTIONNAIRE DE TRADUCTION
# ==============================================================================
# Fait le lien entre les noms de l'API et nos noms internes
API_NAME_TO_INTERNAL_NAME_MAP = {
    # Nom de l'API (clé) : Nom interne (valeur)
    'WODAN - Timburcoaster': 'Wodan',
    'blue fire Megacoaster': 'Blue Fire',
    'Voltron Nevera powered by Rimac': 'Voltron Nevera',
    'ARTHUR': 'Arthur',
    'Eurosat - CanCan Coaster': 'Eurosat',
    'Water rollercoaster Poseidon': 'Poseidon',
    "Alpine Express 'Enzian'": 'Alpine Express',
    'Voletarium': 'Voletarium',
    'Euro-Mir': 'Euro-Mir',
    'Pirates in Batavia': 'Pirates in Batavia',
    'Silver Star': 'Silver Star',
    'Matterhorn-Blitz': 'Matterhorn-Blitz',
    'Castello dei Medici': 'Castello dei Medici',
    'Pegasus': 'Pegasus',
    'Swiss Bob Run': 'Swiss Bob Run',
    'Atlantica SuperSplash': 'Atlantica SuperSplash',
    'Atlantis Adventure': 'Atlantis Adventure'
}
# ==============================================================================
# FIN DE L'AJOUT
# ==============================================================================


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

# Coordonnées (probablement cassées aussi)
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

# --- FONCTIONS DE DONNÉES ---

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
})

def load_historical_data(csv_file: str) -> dict:
    """
    Charge les données historiques depuis le fichier CSV (format large) en mémoire.
    Retourne un dict imbriqué: { 'Attraction': { heure: temps_moyen } }
    """
    data = defaultdict(dict)
    if not os.path.exists(csv_file):
        print(f"ERREUR: Fichier de données historiques '{csv_file}' non trouvé.")
        print("Veuillez exécuter le script 'generate_historical_data.py' (version large) d'abord.")
        return data
        
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            # === LA CORRECTION EST ICI ===
            # Suppression de delimiter=';' car votre nouveau CSV utilise des virgules
            reader = csv.DictReader(f)
            # ===============================
            
            if not reader.fieldnames:
                print(f"ERREUR: Fichier CSV '{csv_file}' est vide.")
                return data
                
            hour_columns = [col for col in reader.fieldnames if col != 'Attraction']

            for row in reader:
                attraction_name = row.get('Attraction')
                if not attraction_name:
                    continue
                
                for hour_str in hour_columns:
                    try:
                        hour_int = int(hour_str)
                        # Remplacer les virgules par des points (sécurité)
                        wait_time_str = row[hour_str].replace(',', '.')
                        
                        wait_time = float(wait_time_str) if wait_time_str else 0.0
                        
                        data[attraction_name][hour_int] = wait_time
                        
                    except (ValueError, TypeError, KeyError) as e:
                        print(f"Avertissement: Donnée invalide pour {attraction_name} @ {hour_str}h. Utilisation de 0.0. Erreur: {e}")
                        data[attraction_name][hour_int] = 0.0
    
    except Exception as e:
        print(f"Erreur lors de la lecture de {csv_file}: {e}")
        
    print(f"✓ Données historiques (format large) chargées depuis '{csv_file}'")
    return data
HISTORICAL_DATA = load_historical_data(HISTORICAL_DATA_FILE)


# ==============================================================================
# MODIFICATION DE LA FONCTION fetch_all_live_wait_times
# ==============================================================================
def fetch_all_live_wait_times() -> dict:
    """
    Récupère tous les temps d'attente "live" via l'API JSON
    et les traduit en utilisant le dictionnaire de mapping.
    """
    live_times = {} # Utilise les noms INTERNES comme clés
    try:
        response = session.get(API_URL, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        for land in data.get('lands', []):
            for ride in land.get('rides', []):
                api_name = ride.get('name') # Nom de l'API (ex: 'WODAN - Timburcoaster')
                
                # Traduire le nom de l'API en nom interne.
                # S'il n'est pas dans le map, utiliser le nom de l'API tel quel.
                internal_name = API_NAME_TO_INTERNAL_NAME_MAP.get(api_name, api_name)
                
                # Vérifier si ce nom (traduit ou original) 
                # est dans notre liste de gestion
                if internal_name in ATTRACTIONS_MASTER_LIST:
                    if ride.get('is_open', False):
                        live_times[internal_name] = float(ride.get('wait_time', 0.0))
                    else:
                        live_times[internal_name] = "CLOSED"
                        
    except requests.exceptions.RequestException as e:
        print(f"Erreur de réseau lors de l'appel à l'API: {e}")
        return {}
    except json.JSONDecodeError:
        print("Erreur: Impossible de décoder la réponse JSON de l'API.")
        return {}
        
    return live_times
# ==============================================================================
# FIN DE LA MODIFICATION
# ==============================================================================


def get_predicted_wait_time(attraction: str, target_hour: int) -> float:
    # (Fonction inchangée)
    if not HISTORICAL_DATA:
        return 0.0 
    return HISTORICAL_DATA.get(attraction, {}).get(target_hour, 0.0)


def calculer_facteur_opportunite(actual_wait, avg_wait):
    # (Fonction inchangée)
    P_RECOMPENSE, P_PENALITE = 2, 3
    if avg_wait is None or actual_wait is None or avg_wait <= 5: return 1.0
    if avg_wait == 0 and actual_wait > 0:
        avg_wait = 1.0 
    ratio = actual_wait / avg_wait
    facteur = ratio ** P_RECOMPENSE if ratio <= 1 else ratio ** P_PENALITE
    return max(0.1, min(facteur, 5.0))

def find_best_next_step(current_location, attractions_to_visit, current_time, virtual_line_details=None):
    # (Fonction inchangée - elle fonctionnera maintenant car 
    # live_wait_times utilisera les bons noms)
    
    travel_times = defaultdict(lambda: float('inf'))
    for loc1, loc2, weight in COMPLETE_EDGES_UNPONDERED:
        travel_times[(loc1, loc2)] = weight
        travel_times[(loc2, loc1)] = weight

    # Cet appel récupère maintenant les données traduites
    live_wait_times = fetch_all_live_wait_times() 
    
    if not live_wait_times:
        print("Avertissement: Impossible de récupérer les temps d'attente live. Les calculs peuvent être faussés.")

    predicted_waits = [
        p for p in (get_predicted_wait_time(attr, current_time.hour) for attr in attractions_to_visit) 
        if p > 0
    ]
    TEMPS_ATTENTE_REFERENCE = sum(predicted_waits) / len(predicted_waits) if predicted_waits else 30

    all_candidates_details = []
    
    vl_datetime_target = None
    if virtual_line_details:
        vl_time = virtual_line_details['time']
        vl_datetime_target = current_time.replace(hour=vl_time.hour, minute=vl_time.minute, second=0, microsecond=0)
        if vl_datetime_target < current_time:
            vl_datetime_target += timedelta(days=1)

    for candidate in attractions_to_visit:
        travel_time = travel_times.get((current_location, candidate), 30) if candidate != current_location else 0.0
        
        # 'candidate' (ex: 'Wodan') correspondra maintenant à la clé dans live_wait_times
        real_current_wait = live_wait_times.get(candidate, "CLOSED") 
        
        end_time, arrival_at_vl, is_late = None, None, False
        
        if real_current_wait == "CLOSED":
            final_cost = float('inf')
            predicted_wait_now = "N/A"
        else:
            predicted_wait_now = get_predicted_wait_time(candidate, current_time.hour)
            total_time_at_candidate = timedelta(minutes=travel_time + real_current_wait + ATTRACTION_RIDE_TIME)
            end_time = current_time + total_time_at_candidate
            
            if virtual_line_details:
                travel_time_to_vl = travel_times.get((candidate, virtual_line_details['attraction']), 30)
                arrival_at_vl = end_time + timedelta(minutes=travel_time_to_vl)
                is_late = arrival_at_vl > (vl_datetime_target + timedelta(minutes=15))
                final_cost = float('inf') if is_late else total_time_at_candidate.total_seconds() / 60
            else:
                facteur_opportunite = calculer_facteur_opportunite(real_current_wait, predicted_wait_now)
                opportunity_cost = TEMPS_ATTENTE_REFERENCE * facteur_opportunite
                final_cost = travel_time + opportunity_cost

        candidate_details = {
            "destination": candidate, 
            "travel_time": travel_time,
            "real_wait_time": real_current_wait,
            "predicted_wait_time": predicted_wait_now,
            "cost": final_cost, 
            "end_time": end_time,
            "arrival_at_vl": arrival_at_vl,
            "is_late": is_late,
        }
        all_candidates_details.append(candidate_details)

    if not all_candidates_details:
        return {"cost": float('inf'), "destination": "N/A"}, []

    if virtual_line_details:
        on_time_candidates = [c for c in all_candidates_details if not c['is_late']]
        late_candidates = [c for c in all_candidates_details if c['is_late']]
        on_time_candidates.sort(key=lambda x: x['cost'])
        late_candidates.sort(key=lambda x: x['arrival_at_vl'] or datetime.max.replace(tzinfo=current_time.tzinfo))
        all_candidates_details = on_time_candidates + late_candidates
    else:
        all_candidates_details.sort(key=lambda x: x['cost'])
        
    best_choice_details = all_candidates_details[0] if all_candidates_details else {"cost": float('inf'), "destination": "N/A"}
        
    return best_choice_details, all_candidates_details

"""
# --- EXEMPLE D'EXÉCUTION (Inchangé) ---
if __name__ == '__main__':
    start_time = time.perf_counter() 
    
    print("--- Démarrage du moteur de calcul d'optimisation (Mode API + CSV Large) ---")
    
    if not HISTORICAL_DATA:
        print("Arrêt du programme. Veuillez générer le fichier CSV.")
    else:
        start_location = 'Entree'
        my_attractions = ['Wodan', 'Blue Fire', 'Silver Star', 'Arthur', 'Voltron Nevera']
        now = datetime.now().replace(hour=10, minute=30) 
        
        print(f"Heure actuelle (simulée): {now.strftime('%H:%M')}")
        print(f"Position actuelle: {start_location}")
        print(f"Attractions à visiter: {my_attractions}")
        print("\nCalcul de la meilleure prochaine étape...")

        # Scénario 1: Pas de Virtual Line
        best_step_no_vl, all_steps_no_vl = find_best_next_step(start_location, my_attractions, now)
        
        print("\n--- Analyse (Sans Virtual Line) ---")
        if best_step_no_vl['destination'] != "N/A":
            print(f"Meilleur choix: **{best_step_no_vl['destination']}**")
            print(f"  Coût (opportunité + voyage): {best_step_no_vl['cost']:.2f}")
            print(f"  Temps de trajet estimé: {best_step_no_vl['travel_time']} min")
            print(f"  Attente actuelle (live): {best_step_no_vl['real_wait_time']} min")
            print(f"  Attente prédite (moyenne): {best_step_no_vl['predicted_wait_time']} min")
        else:
            print("Aucune attraction valide trouvée.")
            
        # Scénario 2: Avec Virtual Line
        vl_details = {
            'attraction': 'Voltron Nevera',
            'time': datetime.now().replace(hour=10, minute=45).time() 
        }
        print(f"\n--- Analyse (Avec VL pour {vl_details['attraction']} à {vl_details['time'].strftime('%H:%M')}) ---")
        
        my_attractions_with_vl = ['Wodan', 'Blue Fire', 'Silver Star', 'Arthur']
        
        best_step_vl, all_steps_vl = find_best_next_step(start_location, my_attractions_with_vl, now, vl_details)
        
        if best_step_vl['destination'] != "N/A":
            print(f"Meilleur choix: **{best_step_vl['destination']}**")
            print(f"  Attente actuelle (live): {best_step_vl['real_wait_time']} min")
            print(f"  Heure de fin estimée: {best_step_vl['end_time'].strftime('%H:%M') if best_step_vl['end_time'] else 'N/A'}")
            print(f"  Arrivée estimée à la VL: {best_step_vl['arrival_at_vl'].strftime('%H:%M') if best_step_vl['arrival_at_vl'] else 'N/A'}")
            print(f"  En retard pour la VL ?: {best_step_vl['is_late']}")
        else:
            print("Aucune attraction valide trouvée permettant d'être à l'heure pour la VL.")

    end_time = time.perf_counter() 
    duration = end_time - start_time
    
    print("-" * 50)
    print(f"Temps d'exécution total du main : {duration:.4f} secondes")
    
"""

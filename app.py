# app.py (Version avec carte Folium)
import streamlit as st
import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime
from collections import defaultdict
from functools import lru_cache
import folium  # Importation de Folium
from streamlit_folium import st_folium # Importation du composant Streamlit

# --- CONFIGURATION ET DONNÉES ---

# (Le reste des constantes comme ATTRACTIONS_MASTER_LIST, URLS, etc. reste identique)
START_LOCATION_DEFAULT = 'Entree'
ATTRACTIONS_MASTER_LIST = [
    'Wodan', 'Blue Fire', 'Voletarium', 'Voltron Nevera', 'Euro-Mir',
    'Pirates in Batavia', 'Silver Star', 'Arthur', 'Matterhorn-Blitz', 'Eurosat', 'Poseidon'
]
URLS = {
    'Blue Fire': 'https://queue-times.com/fr/parks/51/rides/5603', 'Voltron Nevera': 'https://queue-times.com/fr/parks/51/rides/13349',
    'Wodan': 'https://queue-times.com/fr/parks/51/rides/5602', 'Euro-Mir': 'https://queue-times.com/fr/parks/51/rides/5605',
    'Voletarium': 'https://queue-times.com/fr/parks/51/rides/5630', 'Pirates in Batavia': 'https://queue-times.com/fr/parks/51/rides/5617',
    'Silver Star': 'https://queue-times.com/fr/parks/51/rides/5604', 'Arthur': 'https://queue-times.com/fr/parks/51/rides/5618',
    'Matterhorn-Blitz': 'https://queue-times.com/fr/parks/51/rides/5607', 'Eurosat': 'https://queue-times.com/fr/parks/51/rides/5737',
    'Poseidon': 'https://queue-times.com/fr/parks/51/rides/5611'
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
    ('Poseidon', 'Wodan', 19), ('Poseidon', 'Euro-Mir', 5), ('Poseidon', 'Voletarium', 14), ('Entree', 'Blue Fire', 29),
    ('Entree', 'Voltron Nevera', 15), ('Entree', 'Wodan', 30), ('Entree', 'Euro-Mir', 14), ('Entree', 'Voletarium', 1),
    ('Entree', 'Pirates in Batavia', 20), ('Entree', 'Silver Star', 7), ('Entree', 'Arthur', 22), ('Entree', 'Matterhorn-Blitz', 8),
    ('Entree', 'Eurosat', 5), ('Entree', 'Poseidon', 10)
]


# ==============================================================================
# === NOUVELLE SECTION : COORDONNÉES GPS DES ATTRACTIONS ===
# === VEUILLEZ REMPLIR AVEC VOS PROPRES DONNÉES GPS (Latitude, Longitude) ===
# ==============================================================================
ATTRACTIONS_COORDS = {
    'Entree': (48.26886239084585, 7.7218611694409045),
    'Voletarium': (48.26917304513733, 7.722443208799992),
    'Eurosat': (48.267451577912816, 7.72113123949057),
    'Silver Star': (48.26779998024085, 7.720126590003773),
    'Euro-Mir': (48.26507602609998, 7.720178628240745),
    'Wodan': (48.26138819760847, 7.7192129584382885),
    'Blue Fire': (48.26265872340149, 7.718827721822693),
    'Voltron Nevera': (48.2657797944176, 7.719762395202016), # Coordonnées à ajuster
    'Pirates in Batavia': (48.26358868421831, 7.7204499731581135),
    'Arthur': (48.26389057631639, 7.723843203049346),
    'Matterhorn-Blitz': (48.26691168136572, 7.72049900063425),
    'Poseidon': (48.26666361205288, 7.719339791552477)
}
# ==============================================================================

# (Toutes les fonctions utilitaires comme fetch_page_content, dernierTemps, etc. restent identiques)
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
})
RE_CHART_SCRIPT = re.compile(r"var createChart = function")
RE_JSON_DATA = re.compile(r"\[\{\"name\":.*?\}\]", re.DOTALL)
RE_MONTH_CHART = re.compile(r'\[\{"name":".*?","data":(.*?)}\]', re.DOTALL)

@lru_cache(maxsize=None)
def fetch_page_content(url: str) -> str:
    try:
        resp = session.get(url, timeout=10)
        resp.raise_for_status()
        return resp.text
    except requests.exceptions.RequestException as e:
        st.error(f"Erreur de réseau en contactant {url}: {e}")
        return ""

@st.cache_data(ttl=300)
def dernierTemps(attraction: str) -> float:
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

@st.cache_data(ttl=3600)
def predire_temps_attente(attraction: str, heure_cible: int, semaine_cible_num: int, jour_cible: str) -> float:
    if not (9 <= heure_cible <= 20): return 0.0
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
                return hourly_pattern_map.get(heure_cible, 0.0)
            except (json.JSONDecodeError, IndexError):
                return 0.0
    return 0.0

def get_wait_time_ponderation_coefficient(avg_wait, actual_wait):
    if avg_wait is None or actual_wait is None: return 1.0
    diff_wait = avg_wait - actual_wait
    if diff_wait <= 0:
        return 1 + (-diff_wait / 60)**2
    else:
        return actual_wait / avg_wait if avg_wait > 0 else 0.5

def find_best_next_step(current_location, attractions_to_visit, current_time):
    travel_times = defaultdict(lambda: float('inf'))
    for loc1, loc2, weight in COMPLETE_EDGES_UNPONDERED:
        travel_times[(loc1, loc2)] = weight
        travel_times[(loc2, loc1)] = weight

    day_mapping = ['lun', 'mar', 'mer', 'jeu', 'ven', 'sam', 'dim']
    semaine_actuelle = current_time.isocalendar()[1] - 1
    jour_actuel_str = day_mapping[current_time.weekday()]
    best_choice_details = None
    lowest_cost = float('inf')
    
    with st.expander("Voir les détails du calcul pour chaque attraction"):
        for candidate in attractions_to_visit:
            if candidate == current_location: continue
            travel_time = travel_times.get((current_location, candidate), float('inf'))
            if travel_time == float('inf'): continue
            real_current_wait = dernierTemps(candidate)
            predicted_wait_now = predire_temps_attente(
                attraction=candidate, heure_cible=current_time.hour,
                semaine_cible_num=semaine_actuelle, jour_cible=jour_actuel_str
            )
            penalty_coefficient = get_wait_time_ponderation_coefficient(
                avg_wait=predicted_wait_now, actual_wait=real_current_wait
            )
            total_cost = travel_time * penalty_coefficient

            st.markdown(f"--- \n**Candidat : {candidate}**")
            col1, col2, col3 = st.columns(3)
            diff = real_current_wait - predicted_wait_now if predicted_wait_now is not None else 0
            
            col1.metric("Temps de trajet", f"{travel_time:.0f} min")
            col2.metric("Attente (Réel / Prédit)", f"{real_current_wait:.0f} / {predicted_wait_now or 'N/A':.0f} min",
                        delta=f"{diff:.0f} min", delta_color="inverse")
            col3.metric("Coût Final", f"{total_cost:.2f}")
            
            if total_cost < lowest_cost:
                lowest_cost = total_cost
                best_choice_details = {
                    "destination": candidate, "from": current_location, "cost": total_cost,
                    "real_travel_time": travel_time, "real_wait_time_now": real_current_wait,
                }
    
    return best_choice_details

# --- NOUVELLE FONCTION POUR CRÉER LA CARTE ---
def create_park_map(coords, history, current_loc, recommendation):
    """Crée et retourne une carte Folium du parc."""
    # Centrer la carte sur la moyenne des coordonnées
    avg_lat = 48.26552018302352
    avg_lon = 7.729503548291553

    m = folium.Map(location=[avg_lat, avg_lon], zoom_start=15, tiles="CartoDB positron")

    # 1. Dessiner le parcours déjà effectué (en bleu)
    if len(history) > 1:
        path_coords = [coords[loc] for loc in history if loc in coords]
        folium.PolyLine(path_coords, color='blue', weight=4, opacity=0.8, tooltip="Parcours effectué").add_to(m)

    # 2. Dessiner le trajet proposé (en vert D'ABORD, puis devient bleu une fois validé)
    if recommendation:
        start_coord = coords.get(current_loc)
        end_coord = coords.get(recommendation['destination'])
        if start_coord and end_coord:
            folium.PolyLine([start_coord, end_coord], color='green', weight=5,
                            dash_array='10', tooltip="Prochain trajet").add_to(m)

    # 3. Placer les points pour chaque attraction
    for name, location in coords.items():
        icon_color = 'black'
        icon_type = 'info-sign'
        if name == current_loc:
            icon_color = 'blue' # Point bleu pour la position actuelle
            icon_type = 'user'
        elif recommendation and name == recommendation['destination']:
            icon_color = 'green' # Point vert pour la destination proposée
            icon_type = 'flag'
        elif name in history:
            icon_color = 'purple' # Point violet pour les attractions visitées
            icon_type = 'ok-sign'
            
        folium.Marker(
            location=location,
            popup=name,
            tooltip=name,
            icon=folium.Icon(color=icon_color, icon=icon_type, prefix='glyphicon')
        ).add_to(m)
        
    return m

# --- INTERFACE STREAMLIT ---

st.set_page_config(layout="wide", page_title="Optimiseur Europa-Park")

# Initialisation de l'état de la session
if 'attractions_to_visit' not in st.session_state:
    st.session_state.attractions_to_visit = ATTRACTIONS_MASTER_LIST.copy()
if 'current_location' not in st.session_state:
    st.session_state.current_location = START_LOCATION_DEFAULT
if 'last_recommendation' not in st.session_state:
    st.session_state.last_recommendation = None
if 'history' not in st.session_state:
    # L'historique commence toujours par le point de départ
    st.session_state.history = [START_LOCATION_DEFAULT]


st.title("Optimiseur de Visite à Europa-Park")

with st.sidebar:
    st.header("Configuration de votre journée")
    selected_attractions = st.multiselect(
        "Attractions sur votre liste",
        options=ATTRACTIONS_MASTER_LIST,
        default=st.session_state.attractions_to_visit
    )
    if selected_attractions != st.session_state.attractions_to_visit:
        st.session_state.attractions_to_visit = selected_attractions
        st.rerun()

    possible_locations = [START_LOCATION_DEFAULT] + ATTRACTIONS_MASTER_LIST
    current_location_selection = st.selectbox(
        "Position actuelle",
        options=possible_locations,
        index=possible_locations.index(st.session_state.current_location)
    )
    if current_location_selection != st.session_state.current_location:
        st.session_state.current_location = current_location_selection
        st.session_state.history = [current_location_selection] # Réinitialise l'historique si on se "téléporte"
        st.rerun()

    st.info(f"Position actuelle : **{st.session_state.current_location}**")
    
    if st.button("Réinitialiser la journée"):
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()

col1, col2 = st.columns([1, 2])

with col1:
    st.header("Votre Parcours")
    
    # --- REMPLACEMENT DE L'ANCIENNE LISTE PAR LA CARTE ---
    park_map = create_park_map(
        coords=ATTRACTIONS_COORDS,
        history=st.session_state.history,
        current_loc=st.session_state.current_location,
        recommendation=st.session_state.last_recommendation
    )
    st_folium(park_map, width=700, height=500) # Affichage de la carte

with col2:
    st.header("Prochaine Étape")
    
    recommendation_placeholder = st.empty()

    if st.button("Trouver la meilleure prochaine attraction", type="primary", use_container_width=True):
        if not st.session_state.attractions_to_visit:
            st.warning("Votre liste d'attractions à visiter est vide.")
        else:
            with st.spinner("Analyse des temps d'attente et des trajets en cours..."):
                now = datetime.now()
                recommendation = find_best_next_step(
                    st.session_state.current_location,
                    st.session_state.attractions_to_visit,
                    now
                )
                st.session_state.last_recommendation = recommendation
    
    if st.session_state.last_recommendation:
        rec = st.session_state.last_recommendation
        with recommendation_placeholder.container():
            st.success(f"La destination la plus intelligente est **{rec['destination']}** !")
            sub_col1, sub_col2 = st.columns(2)
            sub_col1.metric("Temps de marche estimé", f"{rec['real_travel_time']:.0f} minutes")
            sub_col2.metric("Temps d'attente sur place", f"{rec['real_wait_time_now']:.0f} minutes")
            
            if st.button(f"J'ai fait {rec['destination']}", use_container_width=True):
                last_done = st.session_state.last_recommendation['destination']
                st.session_state.history.append(last_done)
                st.session_state.current_location = last_done
                if last_done in st.session_state.attractions_to_visit:
                    st.session_state.attractions_to_visit.remove(last_done)
                st.session_state.last_recommendation = None
                st.rerun()
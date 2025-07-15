# app.py (Interface Streamlit utilisant le moteur de calcul)
import streamlit as st
from datetime import datetime
import folium
from streamlit_folium import st_folium

# --- IMPORTATION DU MOTEUR DE CALCUL ---
# Toute la logique de calcul est maintenant dans mainCode.py
import mainCode

# --- CONFIGURATION ET CONSTANTES PROPRES À L'INTERFACE ---
START_LOCATION_DEFAULT = 'Entree'
ATTRACTIONS_MASTER_LIST = [
    'Wodan', 'Blue Fire', 'Voletarium', 'Voltron Nevera', 'Euro-Mir',
    'Pirates in Batavia', 'Silver Star', 'Arthur', 'Matterhorn-Blitz', 'Eurosat', 
    'Poseidon', 'Castello dei Medici', 'Pegasus', 'Swiss Bob Run', 
    'Atlantica SuperSplash', 'Alpine Express', 'Atlantis Adventure'
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

# --- FONCTIONS DE L'INTERFACE ---

def create_park_map(coords, history, current_loc, recommendation, attractions_to_visit):
    """Crée la carte Folium du parc."""
    points_to_show = set(attractions_to_visit)
    points_to_show.add(current_loc)
    if recommendation:
        points_to_show.add(recommendation['destination'])

    if not points_to_show:
        center_coords = coords.get(current_loc, (48.266, 7.721))
    else:
        avg_lat = sum(coords[loc][0] for loc in points_to_show if loc in coords) / len(points_to_show)
        avg_lon = sum(coords[loc][1] for loc in points_to_show if loc in coords) / len(points_to_show)
        center_coords = (avg_lat, avg_lon)

    m = folium.Map(location=center_coords, zoom_start=16, tiles="CartoDB positron")

    if len(history) > 1:
        path_coords = [coords[loc] for loc in history if loc in coords]
        folium.PolyLine(path_coords, color='blue', weight=4, opacity=0.8, tooltip="Parcours effectué").add_to(m)

    if recommendation:
        start_coord = coords.get(current_loc)
        end_coord = coords.get(recommendation['destination'])
        if start_coord and end_coord:
            folium.PolyLine([start_coord, end_coord], color='green', weight=5,
                            dash_array='10', tooltip="Prochain trajet").add_to(m)

    for name, location in coords.items():
        if name in points_to_show:
            icon_color, icon_type = 'black', 'info-sign'
            if name == current_loc:
                icon_color, icon_type = 'blue', 'user'
            elif recommendation and name == recommendation['destination']:
                icon_color, icon_type = 'green', 'flag'
            elif name in history:
                icon_color, icon_type = 'purple', 'ok-sign'
                
            folium.Marker(
                location=location, popup=name, tooltip=name,
                icon=folium.Icon(color=icon_color, icon=icon_type, prefix='glyphicon')
            ).add_to(m)
            
    return m

# --- INTERFACE STREAMLIT ---

st.set_page_config(layout="wide", page_title="Optimiseur de Parc")

# Initialisation de l'état de la session
if 'attractions_to_visit' not in st.session_state:
    st.session_state.attractions_to_visit = ATTRACTIONS_MASTER_LIST.copy()
if 'current_location' not in st.session_state:
    st.session_state.current_location = START_LOCATION_DEFAULT
if 'last_recommendation' not in st.session_state:
    st.session_state.last_recommendation = None
if 'history' not in st.session_state:
    st.session_state.history = [START_LOCATION_DEFAULT]

st.title("Optimiseur AfflueMap")

with st.sidebar:
    st.header("Configuration")
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
        st.session_state.history = [current_location_selection]
        st.rerun()

    st.info(f"**Position :** {st.session_state.current_location}")

    if st.button("Réinitialiser la journée"):
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()

# --- Mise en page principale ---
st.header("Prochaine Étape")

if st.button("Trouver la meilleure prochaine attraction", type="primary", use_container_width=True):
    if not st.session_state.attractions_to_visit:
        st.warning("Votre liste d'attractions à visiter est vide.")
    else:
        with st.spinner("Analyse en cours..."):
            now = datetime.now()
            # --- APPEL AU MOTEUR DE CALCUL ---
            # On appelle la fonction importée depuis mainCode.py
            recommendation = mainCode.find_best_next_step(
                current_location=st.session_state.current_location,
                attractions_to_visit=st.session_state.attractions_to_visit,
                travel_times_edges=mainCode.COMPLETE_EDGES_UNPONDERED, # On utilise les données de mainCode
                current_time=now
            )
            st.session_state.last_recommendation = recommendation

# Affichage des résultats
if st.session_state.last_recommendation:
    rec = st.session_state.last_recommendation
    st.success(f"Destination suggérée : **{rec['destination']}** !")
    sub_col1, sub_col2 = st.columns(2)
    sub_col1.metric("Marche", f"~{rec['real_travel_time']:.0f} min")
    sub_col2.metric("Attente", f"~{rec['real_wait_time_now']:.0f} min")
    
    if st.button(f"J'ai fait {rec['destination']}", use_container_width=True):
        last_done = st.session_state.last_recommendation['destination']
        st.session_state.history.append(last_done)
        st.session_state.current_location = last_done
        if last_done in st.session_state.attractions_to_visit:
            st.session_state.attractions_to_visit.remove(last_done)
        st.session_state.last_recommendation = None
        st.rerun()

st.markdown("---")
st.header("Carte du Parc")
park_map = create_park_map(
    coords=ATTRACTIONS_COORDS,
    history=st.session_state.history,
    current_loc=st.session_state.current_location,
    recommendation=st.session_state.last_recommendation,
    attractions_to_visit=st.session_state.attractions_to_visit
)
st_folium(park_map, width='100%', height=400)

st.markdown("---")
with st.expander(f"Votre Plan ({len(st.session_state.attractions_to_visit)} attractions restantes)"):
    if st.session_state.attractions_to_visit:
        for attraction in st.session_state.attractions_to_visit:
            st.markdown(f"- {attraction}")
    else:
        st.success("Vous avez fait toutes les attractions de votre liste !")

    if st.session_state.history and len(st.session_state.history) > 1:
        st.markdown("**Parcours effectué :**")
        st.write(" -> ".join(st.session_state.history))

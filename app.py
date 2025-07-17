# app.py (Interface Streamlit utilisant le moteur de calcul)
import streamlit as st
from datetime import datetime
import folium
from streamlit_folium import st_folium
import mainCode # Importe notre moteur de calcul

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(layout="wide", page_title="Optimiseur de Parc")
START_LOCATION_DEFAULT = 'Entree'

# --- FONCTIONS D'AFFICHAGE ---

def create_park_map(history, current_loc, recommendation, attractions_to_visit):
    """Crée et affiche la carte du parc avec le parcours et la recommandation."""
    coords = mainCode.ATTRACTIONS_COORDS
    points_to_show = set(attractions_to_visit)
    points_to_show.add(current_loc)
    if recommendation:
        points_to_show.add(recommendation['destination'])

    # Centre la carte sur les points pertinents
    if not points_to_show or all(loc not in coords for loc in points_to_show):
        center_coords = (48.266, 7.721) # Coordonnées par défaut
    else:
        valid_points = [loc for loc in points_to_show if loc in coords]
        avg_lat = sum(coords[loc][0] for loc in valid_points) / len(valid_points)
        avg_lon = sum(coords[loc][1] for loc in valid_points) / len(valid_points)
        center_coords = (avg_lat, avg_lon)

    m = folium.Map(location=center_coords, zoom_start=15, tiles="CartoDB positron")

    # Affiche le parcours déjà effectué
    if len(history) > 1:
        path_coords = [coords[loc] for loc in history if loc in coords]
        if path_coords:
            folium.PolyLine(path_coords, color='blue', weight=4, opacity=0.8, tooltip="Parcours effectué").add_to(m)

    # Affiche le trajet recommandé
    if recommendation:
        start_coord = coords.get(current_loc)
        end_coord = coords.get(recommendation['destination'])
        if start_coord and end_coord:
            folium.PolyLine([start_coord, end_coord], color='green', weight=5,
                            dash_array='10', tooltip="Prochain trajet").add_to(m)

    # Affiche les marqueurs pour chaque attraction
    for name, location in coords.items():
        if name in points_to_show:
            icon_color, icon_type = 'gray', 'info-sign'
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

# --- INITIALISATION DE L'ÉTAT DE LA SESSION ---
if 'attractions_to_visit' not in st.session_state:
    st.session_state.attractions_to_visit = mainCode.ATTRACTIONS_MASTER_LIST.copy()
if 'current_location' not in st.session_state:
    st.session_state.current_location = START_LOCATION_DEFAULT
if 'last_recommendation' not in st.session_state:
    st.session_state.last_recommendation = None
if 'all_candidates' not in st.session_state:
    st.session_state.all_candidates = None
if 'history' not in st.session_state:
    st.session_state.history = [START_LOCATION_DEFAULT]

# --- INTERFACE PRINCIPALE ---

st.title("Optimiseur AfflueMap")

# --- BARRE LATÉRALE DE CONFIGURATION ---
with st.sidebar:
    st.header("Configuration")
    selected_attractions = st.multiselect(
        "Attractions sur votre liste",
        options=mainCode.ATTRACTIONS_MASTER_LIST,
        default=st.session_state.attractions_to_visit
    )
    if selected_attractions != st.session_state.attractions_to_visit:
        st.session_state.attractions_to_visit = selected_attractions
        st.rerun()

    possible_locations = [START_LOCATION_DEFAULT] + mainCode.ATTRACTIONS_MASTER_LIST
    current_location_selection = st.selectbox(
        "Position actuelle",
        options=possible_locations,
        index=possible_locations.index(st.session_state.current_location)
    )
    if current_location_selection != st.session_state.current_location:
        st.session_state.current_location = current_location_selection
        st.session_state.history = [current_location_selection] # Réinitialise l'historique si on change de lieu manuellement
        st.rerun()

    st.info(f"**Position :** {st.session_state.current_location}")

    if st.button("Réinitialiser la journée"):
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()

# --- SECTION PRINCIPALE : RECOMMANDATION ---
st.header("Prochaine Étape")

if st.button("Trouver la meilleure prochaine attraction", type="primary", use_container_width=True):
    if not st.session_state.attractions_to_visit:
        st.warning("Votre liste d'attractions à visiter est vide.")
    else:
        with st.spinner("Analyse en cours..."):
            now = datetime.now()
            recommendation, all_candidates = mainCode.find_best_next_step(
                st.session_state.current_location,
                st.session_state.attractions_to_visit,
                now
            )
            st.session_state.last_recommendation = recommendation
            st.session_state.all_candidates = all_candidates

# Affiche la recommandation si elle existe
recommendation_placeholder = st.container()
if st.session_state.last_recommendation:
    rec = st.session_state.last_recommendation
    with recommendation_placeholder:
        st.success(f"Destination suggérée : **{rec['destination']}** !")
        sub_col1, sub_col2 = st.columns(2)
        sub_col1.metric("Marche", f"~{rec['travel_time']:.0f} min")
        sub_col2.metric("Attente", f"~{rec['real_wait_time']:.0f} min")

        if st.button(f"J'ai fait {rec['destination']}", use_container_width=True):
            last_done = st.session_state.last_recommendation['destination']
            st.session_state.history.append(last_done)
            st.session_state.current_location = last_done
            if last_done in st.session_state.attractions_to_visit:
                st.session_state.attractions_to_visit.remove(last_done)
            # Réinitialiser les recommandations pour forcer un nouveau calcul
            st.session_state.last_recommendation = None
            st.session_state.all_candidates = None
            st.rerun()

# Affiche les détails du calcul si disponibles
if st.session_state.all_candidates:
    with st.expander("Voir les détails du calcul", expanded=False):
        for candidate in sorted(st.session_state.all_candidates, key=lambda x: x['cost']):
            st.markdown(f"--- \n**Candidat : {candidate['destination']}**")
            col1, col2, col3 = st.columns(3)
            
            predicted_display = f"{candidate['predicted_wait_time']:.0f}" if candidate['predicted_wait_time'] is not None else "N/A"
            metric_value = f"{candidate['real_wait_time']:.0f} / {predicted_display} min"
            diff = candidate['real_wait_time'] - candidate['predicted_wait_time'] if candidate['predicted_wait_time'] is not None else 0

            col1.metric("Trajet", f"{candidate['travel_time']:.0f} min")
            col2.metric("Attente (Réel/Prédit)", metric_value,
                        delta=f"{diff:.0f} min", delta_color="inverse")
            col3.metric("Coût", f"{candidate['cost']:.2f}")

st.markdown("---")

# --- CARTE DU PARC ---
st.header("Carte du Parc")
park_map = create_park_map(
    history=st.session_state.history,
    current_loc=st.session_state.current_location,
    recommendation=st.session_state.last_recommendation,
    attractions_to_visit=st.session_state.attractions_to_visit
)
st_folium(park_map, width='100%', height=400)

st.markdown("---")

# --- PLAN ET HISTORIQUE ---
with st.expander(f"Votre Plan ({len(st.session_state.attractions_to_visit)} attractions restantes)"):
    if st.session_state.attractions_to_visit:
        for attraction in st.session_state.attractions_to_visit:
            st.markdown(f"- {attraction}")
    else:
        st.success("Vous avez fait toutes les attractions de votre liste !")

    if len(st.session_state.history) > 1:
        st.markdown("**Parcours effectué :**")
        st.write(" -> ".join(st.session_state.history))

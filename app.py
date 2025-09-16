# app.py (Interface Streamlit utilisant le moteur de calcul)
import streamlit as st
from datetime import datetime
import pytz
import folium
from streamlit_folium import st_folium
import mainCode # Importe notre moteur de calcul
from streamlit_geolocation import streamlit_geolocation

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

    if not points_to_show or all(loc not in coords for loc in points_to_show):
        center_coords = (48.266, 7.721)
    else:
        valid_points = [loc for loc in points_to_show if loc in coords]
        avg_lat = sum(coords[loc][0] for loc in valid_points) / len(valid_points)
        avg_lon = sum(coords[loc][1] for loc in valid_points) / len(valid_points)
        center_coords = (avg_lat, avg_lon)

    m = folium.Map(location=center_coords, zoom_start=15, tiles="CartoDB positron")

    if len(history) > 1:
        path_coords = [coords[loc] for loc in history if loc in coords]
        if path_coords:
            folium.PolyLine(path_coords, color='blue', weight=4, opacity=0.8, tooltip="Parcours effectué").add_to(m)

    if recommendation:
        start_coord = coords.get(current_loc)
        end_coord = coords.get(recommendation['destination'])
        if start_coord and end_coord:
            folium.PolyLine([start_coord, end_coord], color='green', weight=5,
                            dash_array='10', tooltip="Prochain trajet").add_to(m)

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

# --- FONCTIONS UTILITAIRES ---

def update_url_state():
    """Met à jour les paramètres de l'URL avec l'état actuel de la session."""
    st.query_params["history"] = ",".join(st.session_state.history)
    st.query_params["attractions_to_visit"] = ",".join(st.session_state.attractions_to_visit)

def find_closest_attraction(user_lat, user_lon):
    """Trouve l'attraction la plus proche à partir des coordonnées de l'utilisateur."""
    if user_lat is None or user_lon is None:
        return START_LOCATION_DEFAULT

    closest_attraction = None
    min_dist_sq = float('inf')

    for attraction, coords in mainCode.ATTRACTIONS_COORDS.items():
        dist_sq = (coords[0] - user_lat)**2 + (coords[1] - user_lon)**2
        if dist_sq < min_dist_sq:
            min_dist_sq = dist_sq
            closest_attraction = attraction
            
    return closest_attraction

st.title("Optimiseur AfflueMap")

# Étape 1 : Obtenir la géolocalisation
location_data = streamlit_geolocation()

# Étape 2 : Conditionner l'affichage du reste de l'application
if location_data and location_data.get('latitude') is not None:

    # --- INITIALISATION DE L'ÉTAT DE LA SESSION (une seule fois) ---
    if 'initialized' not in st.session_state:
        params = st.query_params.to_dict()
        history_from_url = params.get('history', "").split(',') if params.get('history') else []

        if history_from_url:
            st.session_state.history = history_from_url
            st.session_state.current_location = st.session_state.history[-1]
        else:
            initial_pos = find_closest_attraction(location_data['latitude'], location_data['longitude'])
            st.toast(f"Position initiale définie sur : **{initial_pos}** (la plus proche).", icon="📍")
            st.session_state.history = [initial_pos]
            st.session_state.current_location = initial_pos

        attractions_from_url_raw = params.get('attractions_to_visit', "")
        attractions_from_url = attractions_from_url_raw.split(',') if attractions_from_url_raw else []

        if attractions_from_url:
             st.session_state.attractions_to_visit = attractions_from_url
        else:
            st.session_state.attractions_to_visit = mainCode.ATTRACTIONS_MASTER_LIST.copy()
        
        st.session_state.last_recommendation = None
        st.session_state.all_candidates = None
        st.session_state.initialized = True
        update_url_state()

    # --- BARRE LATÉRALE DE CONFIGURATION ---
    with st.sidebar:
        st.header("Soutenir le projet")
        st.write("Si cet outil vous est utile, vous pouvez m'aider à le développer")
        st.link_button("Soutenir", "https://www.buymeacoffee.com/nat4K", use_container_width=True)
        
        st.markdown("---")
        st.header("Configuration")
        
        selected_attractions = st.multiselect(
            "Attractions sur votre liste",
            options=mainCode.ATTRACTIONS_MASTER_LIST,
            default=st.session_state.attractions_to_visit
        )
        if selected_attractions != st.session_state.attractions_to_visit:
            st.session_state.attractions_to_visit = selected_attractions
            update_url_state()
            st.rerun()

        st.markdown("---")
        st.info(f"** Position de départ :**\n\n**{st.session_state.current_location}**")
        
        if st.button("Actualiser ma position", help="Utilise votre GPS pour trouver l'attraction la plus proche et l'utiliser comme nouveau point de départ."):
            closest = find_closest_attraction(location_data['latitude'], location_data['longitude'])
            st.session_state.current_location = closest
            st.toast(f"Position actualisée : {closest}", icon="🔄")
            st.rerun()
        
        st.markdown("---")
        if st.button("Réinitialiser la journée"):
            for key in list(st.session_state.keys()): del st.session_state[key]
            st.query_params.clear()
            st.rerun()

    # --- CORPS PRINCIPAL DE L'APPLICATION ---
    st.header("Prochaine Étape")

    if st.button("Trouver la meilleure prochaine attraction", type="primary", use_container_width=True):
        if not st.session_state.attractions_to_visit:
            st.warning("Votre liste d'attractions à visiter est vide.")
        else:
            with st.spinner("Analyse en cours..."):
                fuseau_horaire_parc = pytz.timezone('Europe/Berlin')
                now = datetime.now(fuseau_horaire_parc)
                recommendation, all_candidates = mainCode.find_best_next_step(
                    st.session_state.current_location,
                    st.session_state.attractions_to_visit,
                    now
                )
                st.session_state.last_recommendation = recommendation
                st.session_state.all_candidates = all_candidates

    recommendation_placeholder = st.container()
    if st.session_state.last_recommendation:
        rec = st.session_state.last_recommendation
        with recommendation_placeholder:
            st.success(f"Destination suggérée : **{rec['destination']}** !")
            sub_col1, sub_col2 = st.columns(2)
            
            # Début de la modification : Gère l'affichage pour les attractions fermées
            real_wait = rec['real_wait_time']
            if real_wait == "CLOSED":
                wait_display = "Fermé"
            else:
                wait_display = f"~{real_wait:.0f} min"
            # Fin de la modification

            sub_col1.metric("Marche", f"~{rec['travel_time']:.0f} min")
            sub_col2.metric("Attente", wait_display)

            if st.button(f"J'ai fait {rec['destination']}", use_container_width=True):
                last_done = st.session_state.last_recommendation['destination']
                st.session_state.history.append(last_done)
                st.session_state.current_location = last_done
                if last_done in st.session_state.attractions_to_visit:
                    st.session_state.attractions_to_visit.remove(last_done)
                
                st.session_state.last_recommendation = None
                st.session_state.all_candidates = None
                update_url_state()
                st.rerun()

    # Affiche les détails du calcul si disponibles
    if st.session_state.all_candidates:
        with st.expander("Voir les détails du calcul", expanded=False):
            for candidate in sorted(st.session_state.all_candidates, key=lambda x: x['cost']):
                st.markdown(f"--- \n**Candidat : {candidate['destination']}**")
                col1, col2, col3 = st.columns(3)
                
                # Début de la modification : Logique robuste pour l'affichage des détails
                real_wait = candidate['real_wait_time']
                predicted_wait = candidate['predicted_wait_time']

                if real_wait == "CLOSED":
                    metric_value = "Fermé"
                    delta_value = None
                    delta_color = "off"
                else:
                    predicted_display = f"{predicted_wait:.0f}" if isinstance(predicted_wait, (int, float)) else "N/A"
                    metric_value = f"{real_wait:.0f} / {predicted_display} min"
                    
                    if isinstance(predicted_wait, (int, float)):
                        diff = real_wait - predicted_wait
                        delta_value = f"{diff:.0f} min"
                    else:
                        delta_value = None
                    delta_color = "inverse"
                # Fin de la modification

                col1.metric("Trajet", f"{candidate['travel_time']:.0f} min")
                col2.metric("Attente (Réel/Prédit)", metric_value,
                            delta=delta_value, delta_color=delta_color)
                col3.metric("Coût", f"{candidate['cost']:.2f}" if candidate['cost'] != float('inf') else "N/A")
    
    st.markdown("---")

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

# Étape 3 : Afficher un message d'attente si la position n'est pas encore disponible
else:
    st.warning("En attente de l'autorisation de géolocalisation...")
    st.info("Veuillez autoriser l'accès à votre position dans votre navigateur (vous devrez peut-être cliquer sur l'icône de boussole) pour démarrer l'application.")

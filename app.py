# app.py (Version optimisée pour mobile)
import streamlit as st
import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime
from collections import defaultdict
from functools import lru_cache
import folium
from streamlit_folium import st_folium

# --- TOUTE LA CONFIGURATION ET LES FONCTIONS RESTENT INCHANGÉES ---
# (ATTRACTIONS_MASTER_LIST, URLS, COMPLETE_EDGES_UNPONDERED, ATTRACTIONS_COORDS, 
#  et toutes les fonctions comme fetch_page_content, find_best_next_step, create_park_map, etc.)

# ... (collez ici tout le code des constantes et des fonctions de la version précédente) ...
# Par souci de clarté, je ne répète pas les 200+ lignes de code qui ne changent pas.
# Assurez-vous que toutes vos fonctions sont bien présentes dans votre script.
# La seule partie qui change est l'interface principale ci-dessous.

# --- INTERFACE STREAMLIT (SECTION MODIFIÉE) ---

st.set_page_config(layout="wide", page_title="Optimiseur Europa-Park")

# Initialisation de l'état de la session (inchangée)
if 'attractions_to_visit' not in st.session_state:
    st.session_state.attractions_to_visit = ATTRACTIONS_MASTER_LIST.copy()
if 'current_location' not in st.session_state:
    st.session_state.current_location = START_LOCATION_DEFAULT
if 'last_recommendation' not in st.session_state:
    st.session_state.last_recommendation = None
if 'history' not in st.session_state:
    st.session_state.history = [START_LOCATION_DEFAULT]


st.title("🎢 Optimiseur de Visite")

# La barre latérale est déjà adaptée au mobile (elle se transforme en menu burger)
# Nous la gardons donc telle quelle.
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

    st.info(f"📍 **Position :** {st.session_state.current_location}")

    if st.button("Réinitialiser la journée"):
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()

# ==============================================================================
# === NOUVELLE MISE EN PAGE PRINCIPALE (SANS COLONNES) ===
# ==============================================================================

# 1. Affichage de la carte en premier
st.header("🗺️ Carte et Prochaine Étape")
park_map = create_park_map(
    coords=ATTRACTIONS_COORDS,
    history=st.session_state.history,
    current_loc=st.session_state.current_location,
    recommendation=st.session_state.last_recommendation
)
# Pour mobile, nous pouvons réduire légèrement la hauteur par défaut de la carte
st_folium(park_map, width='100%', height=400)


# 2. Bouton d'action principal juste sous la carte
if st.button("💡 Trouver la meilleure prochaine attraction", type="primary", use_container_width=True):
    if not st.session_state.attractions_to_visit:
        st.warning("Votre liste d'attractions à visiter est vide.")
    else:
        with st.spinner("Analyse en cours..."):
            now = datetime.now()
            recommendation = find_best_next_step(
                st.session_state.current_location,
                st.session_state.attractions_to_visit,
                now
            )
            st.session_state.last_recommendation = recommendation


# 3. Affichage des résultats
recommendation_placeholder = st.container()
if st.session_state.last_recommendation:
    rec = st.session_state.last_recommendation
    with recommendation_placeholder:
        st.success(f"Destination suggérée : **{rec['destination']}** !")
        
        # Utilisation de colonnes ici pour un affichage compact des métriques
        sub_col1, sub_col2 = st.columns(2)
        sub_col1.metric("🚶‍♂️ Marche", f"~{rec['real_travel_time']:.0f} min")
        sub_col2.metric("⏱️ Attente", f"~{rec['real_wait_time_now']:.0f} min")
        
        if st.button(f"✅ J'ai fait {rec['destination']}", use_container_width=True):
            last_done = st.session_state.last_recommendation['destination']
            st.session_state.history.append(last_done)
            st.session_state.current_location = last_done
            if last_done in st.session_state.attractions_to_visit:
                st.session_state.attractions_to_visit.remove(last_done)
            st.session_state.last_recommendation = None
            st.rerun()


# 4. Informations secondaires dans des menus dépliants
st.markdown("---")
with st.expander(f"Votre Plan ({len(st.session_state.attractions_to_visit)} attractions restantes)"):
    if st.session_state.attractions_to_visit:
        for attraction in st.session_state.attractions_to_visit:
            st.markdown(f"- {attraction}")
    else:
        st.success("🎉 Vous avez fait toutes les attractions de votre liste !")

    if st.session_state.history and len(st.session_state.history) > 1:
        st.markdown("**Parcours effectué :**")
        st.write(" -> ".join(st.session_state.history))

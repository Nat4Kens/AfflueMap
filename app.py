# app.py

import streamlit as st
import mainCode
import datetime
from PIL import Image
from collections import defaultdict
import time
import re
import json
import requests
from bs4 import BeautifulSoup
import numpy as np

# --- CONFIGURATION DE L'APPLICATION STREAMLIT ---
st.set_page_config(page_title="AfflueMap - Europa-Park Optimizer", layout="wide")

# --- DONNÉES ET VARIABLES ---
# Pas d'initialisation de session de connexion
travel_times = mainCode.travel_times_from_to
attractions_list = sorted(list(mainCode.URLS.keys()))


# --- FONCTIONS LOCALES POUR L'APPLICATION ---

def fetch_page_unauthenticated(url):
    """Récupère le contenu d'une page sans session authentifiée."""
    try:
        response = requests.get(url, timeout=10, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        st.error(f"Erreur de réseau en contactant l'attraction: {e}")
        return ""

def get_live_wait_time(attraction_name):
    """Obtient le temps d'attente en direct en utilisant la nouvelle fonction non authentifiée."""
    url = mainCode.URLS.get(attraction_name)
    if not url: return "N/A"
    try:
        # On utilise notre nouvelle fonction locale
        html = fetch_page_unauthenticated(url)
        if not html: return "Erreur"
        
        soup = BeautifulSoup(html, 'html.parser')
        wait_time_tag = soup.select_one(".rank-number-wd-lg")
        if wait_time_tag:
            return wait_time_tag.get_text(strip=True)
        return "Fermé"
    except Exception:
        return "Erreur"

# On assigne notre fonction locale pour que mainCode puisse l'utiliser
mainCode.dernierTemps = get_live_wait_time


# --- INTERFACE UTILISATEUR ---

# Titre et description
st.title("🎢 AfflueMap - Votre optimiseur pour Europa-Park")
st.markdown("Planifiez votre journée en temps réel pour minimiser les temps d'attente !")

# Initialisation de l'état de session
if 'attractions_left' not in st.session_state:
    st.session_state.attractions_left = attractions_list.copy()
if 'current_location' not in st.session_state:
    st.session_state.current_location = 'Entree'
if 'parcours' not in st.session_state:
    st.session_state.parcours = []

# --- Colonnes pour l'affichage ---
col1, col2 = st.columns([1, 2])

with col1:
    st.header("📍 Votre Position")
    st.session_state.current_location = st.selectbox(
        "Où êtes-vous actuellement ?",
        options=['Entree'] + attractions_list,
        index=(['Entree'] + attractions_list).index(st.session_state.current_location)
    )

    st.header("✅ Attractions à faire")
    attractions_selected = st.multiselect(
        "Quelles attractions voulez-vous faire aujourd'hui ?",
        options=attractions_list,
        default=st.session_state.attractions_left
    )
    
    # Mettre à jour la liste des attractions restantes si la sélection change
    if set(attractions_selected) != set(st.session_state.attractions_left):
        st.session_state.attractions_left = attractions_selected
        st.experimental_rerun()

with col2:
    st.header("🚀 Prochaine Destination")
    
    # Bouton pour obtenir la recommandation
    if st.button("Trouver la meilleure prochaine attraction !"):
        if not st.session_state.attractions_left:
            st.warning("Veuillez sélectionner au moins une attraction à faire.")
        else:
            with st.spinner("Analyse des temps d'attente et des trajets en cours..."):
                now = datetime.datetime.now()
                
                recommendation = mainCode.find_best_next_step(
                    current_location=st.session_state.current_location,
                    attractions_to_visit=st.session_state.attractions_left,
                    travel_times_edges=mainCode.travel_times_from_to,
                    current_time=now,
                    verbose=True
                )

            if recommendation:
                st.success(f"**Allez à : {recommendation['destination']}**")
                st.write(f"Temps de trajet estimé : **{recommendation['travel_time']:.0f} minutes**")
                st.write(f"Temps d'attente actuel : **{recommendation['current_wait']}**")

                # Mettre à jour le parcours
                st.session_state.parcours.append(recommendation['destination'])
                st.session_state.current_location = recommendation['destination']
                st.session_state.attractions_left.remove(recommendation['destination'])
                
                time.sleep(1)
                st.experimental_rerun()
            else:
                st.error("Impossible de trouver une recommandation. Avez-vous terminé toutes vos attractions ?")

# Affichage du parcours et des attractions restantes
st.header("📋 Votre Journée")
col_parcours, col_restantes = st.columns(2)

with col_parcours:
    st.subheader("Parcours effectué :")
    if st.session_state.parcours:
        for i, attraction in enumerate(st.session_state.parcours):
            st.markdown(f"{i+1}. {attraction}")
    else:
        st.info("Votre parcours est vide pour l'instant.")

with col_restantes:
    st.subheader("Attractions restantes :")
    if st.session_state.attractions_left:
        for attraction in st.session_state.attractions_left:
            st.markdown(f"- {attraction}")
    else:
        st.success("Félicitations, vous avez fait toutes les attractions sélectionnées !")

# Bouton de réinitialisation
if st.button("Réinitialiser la journée"):
    st.session_state.attractions_left = attractions_list.copy()
    st.session_state.current_location = 'Entree'
    st.session_state.parcours = []
    st.experimental_rerun()

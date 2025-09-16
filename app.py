# app.py (Interface Streamlit utilisant le moteur de calcul)
import streamlit as st
from datetime import datetime
import pytz
import folium
from streamlit_folium import st_folium
import mainCode # Importe notre moteur de calcul
import translations # <-- 1. Importer le nouveau module de traduction
from streamlit_geolocation import streamlit_geolocation

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(layout="wide", page_title="Optimiseur AfflueMap")
START_LOCATION_DEFAULT = 'Entree'

# --- GESTION DE LA LANGUE ---

# Fonction pour changer la langue dans le session_state
def set_language(lang_code):
    st.session_state.lang = lang_code

# Initialisation de la langue (français par défaut)
if 'lang' not in st.session_state:
    st.session_state.lang = 'fr'

# Obtenir la fonction de traduction pour la langue actuelle
t = translations.get_translator(st.session_state.lang)

# --- FONCTIONS D'AFFICHAGE ---

def create_park_map(history, current_loc, recommendation, attractions_to_visit):
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
            folium.PolyLine(path_coords, color='blue', weight=4, opacity=0.8, tooltip=t("path_done")).add_to(m)

    if recommendation:
        start_coord = coords.get(current_loc)
        end_coord = coords.get(recommendation['destination'])
        if start_coord and end_coord:
            folium.PolyLine([start_coord, end_coord], color='green', weight=5,
                            dash_array='10', tooltip=t("next_step_header")).add_to(m)

    for name, location in coords.items():
        if name in points_to_show:
            icon_color, icon_type = 'gray', 'info-sign'
            if name == current_loc: icon_color, icon_type = 'blue', 'user'
            elif recommendation and name == recommendation['destination']: icon_color, icon_type = 'green', 'flag'
            elif name in history: icon_color, icon_type = 'purple', 'ok-sign'
            folium.Marker(location=location, popup=name, tooltip=name, icon=folium.Icon(color=icon_color, icon=icon_type, prefix='glyphicon')).add_to(m)
    return m

# --- FONCTIONS UTILITAIRES ---

def update_url_state():
    st.query_params["history"] = ",".join(st.session_state.history)
    st.query_params["attractions_to_visit"] = ",".join(st.session_state.attractions_to_visit)

def find_closest_attraction(user_lat, user_lon):
    if user_lat is None or user_lon is None: return START_LOCATION_DEFAULT
    closest_attraction = None
    min_dist_sq = float('inf')
    for attraction, coords in mainCode.ATTRACTIONS_COORDS.items():
        dist_sq = (coords[0] - user_lat)**2 + (coords[1] - user_lon)**2
        if dist_sq < min_dist_sq:
            min_dist_sq = dist_sq
            closest_attraction = attraction
    return closest_attraction

st.title(t("app_title")) # <-- 2. Remplacer les textes par des appels à `t()`

location_data = streamlit_geolocation()

if location_data and location_data.get('latitude') is not None:
    if 'initialized' not in st.session_state:
        params = st.query_params.to_dict()
        history_from_url = params.get('history', "").split(',') if params.get('history') else []
        if history_from_url:
            st.session_state.history = history_from_url
            st.session_state.current_location = st.session_state.history[-1]
        else:
            initial_pos = find_closest_attraction(location_data['latitude'], location_data['longitude'])
            st.toast(t("initial_pos_toast", pos=initial_pos), icon="📍")
            st.session_state.history = [initial_pos]
            st.session_state.current_location = initial_pos
        attractions_from_url_raw = params.get('attractions_to_visit', "")
        attractions_from_url = attractions_from_url_raw.split(',') if attractions_from_url_raw else []
        if attractions_from_url: st.session_state.attractions_to_visit = attractions_from_url
        else: st.session_state.attractions_to_visit = mainCode.ATTRACTIONS_MASTER_LIST.copy()
        st.session_state.last_recommendation = None
        st.session_state.all_candidates = None
        st.session_state.initialized = True
        update_url_state()

    with st.sidebar:
        # --- 3. AJOUT DU SÉLECTEUR DE LANGUE ---
        st.header("Language / Langue / Sprache")
        col1, col2, col3 = st.columns(3) 
        with col1:
            st.button("🇬🇧", on_click=set_language, args=('en',), use_container_width=True)
        with col2:
            st.button("🇫🇷", on_click=set_language, args=('fr',), use_container_width=True)
        with col3:
            st.button("🇩🇪", on_click=set_language, args=('de',), use_container_width=True)
        st.markdown("---")
        
        st.header(t("support_header"))
        st.write(t("support_text"))
        st.link_button(t("support_button"), "https://www.buymeacoffee.com/nat4K", use_container_width=True)
        st.markdown("---")
        st.header(t("config_header"))
        selected_attractions = st.multiselect(t("attractions_select"), options=mainCode.ATTRACTIONS_MASTER_LIST, default=st.session_state.attractions_to_visit)
        if selected_attractions != st.session_state.attractions_to_visit:
            st.session_state.attractions_to_visit = selected_attractions
            update_url_state()
            st.rerun()
        st.markdown("---")
        st.info(t("start_pos_info", location=st.session_state.current_location))
        if st.button(t("refresh_pos_button"), help=t("refresh_pos_help")):
            closest = find_closest_attraction(location_data['latitude'], location_data['longitude'])
            st.session_state.current_location = closest
            st.toast(t("pos_updated_toast", pos=closest), icon="🔄")
            st.rerun()
        st.markdown("---")
        if st.button(t("reset_day_button")):
            for key in list(st.session_state.keys()): del st.session_state[key]
            st.query_params.clear()
            st.rerun()

    st.header(t("next_step_header"))
    if st.button(t("find_best_button"), type="primary", use_container_width=True):
        if not st.session_state.attractions_to_visit:
            st.warning(t("empty_list_warning"))
        else:
            with st.spinner(t("analysis_in_progress")):
                fuseau_horaire_parc = pytz.timezone('Europe/Berlin')
                now = datetime.now(fuseau_horaire_parc)
                recommendation, all_candidates = mainCode.find_best_next_step(st.session_state.current_location, st.session_state.attractions_to_visit, now)
                st.session_state.last_recommendation = recommendation
                st.session_state.all_candidates = all_candidates

    recommendation_placeholder = st.container()
    if st.session_state.last_recommendation:
        rec = st.session_state.last_recommendation
        with recommendation_placeholder:
            st.success(t("suggested_destination", destination=rec['destination']))
            sub_col1, sub_col2 = st.columns(2)
            real_wait = rec['real_wait_time']
            wait_display = t("closed") if real_wait == "CLOSED" else f"~{real_wait:.0f} {t('minutes_abbr')}"
            sub_col1.metric(t("travel_metric"), f"~{rec['travel_time']:.0f} {t('minutes_abbr')}")
            sub_col2.metric(t("wait_metric"), wait_display)
            if st.button(t("done_button", destination=rec['destination']), use_container_width=True):
                last_done = st.session_state.last_recommendation['destination']
                st.session_state.history.append(last_done)
                st.session_state.current_location = last_done
                if last_done in st.session_state.attractions_to_visit:
                    st.session_state.attractions_to_visit.remove(last_done)
                st.session_state.last_recommendation = None
                st.session_state.all_candidates = None
                update_url_state()
                st.rerun()

    if st.session_state.all_candidates:
        with st.expander(t("show_details_expander"), expanded=False):
            for candidate in sorted(st.session_state.all_candidates, key=lambda x: x['cost']):
                st.markdown(f"--- \n**{t('candidate_header', destination=candidate['destination'])}**")
                col1, col2, col3 = st.columns(3)
                real_wait = candidate['real_wait_time']
                predicted_wait = candidate['predicted_wait_time']
                if real_wait == "CLOSED":
                    metric_value, delta_value, delta_color = t("closed"), None, "off"
                else:
                    predicted_display = f"{predicted_wait:.0f}" if isinstance(predicted_wait, (int, float)) else t("not_applicable_abbr")
                    metric_value = f"{real_wait:.0f} / {predicted_display} {t('minutes_abbr')}"
                    if isinstance(predicted_wait, (int, float)): diff = real_wait - predicted_wait; delta_value = f"{diff:.0f} {t('minutes_abbr')}"
                    else: delta_value = None
                    delta_color = "inverse"
                col1.metric(t("travel_details"), f"{candidate['travel_time']:.0f} {t('minutes_abbr')}")
                col2.metric(t("wait_details"), metric_value, delta=delta_value, delta_color=delta_color)
                cost_display = f"{candidate['cost']:.2f}" if candidate['cost'] != float('inf') else t("not_applicable_abbr")
                col3.metric(t("cost_details"), cost_display)
    
    st.markdown("---")
    st.header(t("park_map_header"))
    park_map = create_park_map(history=st.session_state.history, current_loc=st.session_state.current_location, recommendation=st.session_state.last_recommendation, attractions_to_visit=st.session_state.attractions_to_visit)
    st_folium(park_map, width='100%', height=400)
    st.markdown("---")
    
    with st.expander(t("plan_expander_title", count=len(st.session_state.attractions_to_visit))):
        if st.session_state.attractions_to_visit:
            for attraction in st.session_state.attractions_to_visit: st.markdown(f"- {attraction}")
        else:
            st.success(t("all_attractions_done"))
        if len(st.session_state.history) > 1:
            st.markdown(f"**{t('path_done')}**")
            st.write(" -> ".join(st.session_state.history))
else:
    st.warning(t("geolocation_waiting"))
    st.info(t("geolocation_info"))

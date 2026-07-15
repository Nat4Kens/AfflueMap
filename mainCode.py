# app.py (Interface Streamlit utilisant le moteur de calcul)
import streamlit as st
from datetime import datetime, time, timedelta
import pytz
import folium
from folium.features import DivIcon # Important : Importer DivIcon
from streamlit_folium import st_folium
import mainCode # Importe notre moteur de calcul
import translations # Importe le module de traduction
from streamlit_geolocation import streamlit_geolocation
import math

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(layout="wide", page_title="Optimiseur AfflueMap", initial_sidebar_state="expanded")
START_LOCATION_DEFAULT = 'Entree'

# --- FONCTIONS UTILITAIRES ---
def round_up_time(dt: datetime, minute_step: int = 10) -> datetime:
    """Arrondit un datetime au prochain multiple de `minute_step`."""
    minutes = dt.hour * 60 + dt.minute
    next_minutes = math.ceil((minutes + 1e-9) / minute_step) * minute_step
    if next_minutes == minutes:
        next_minutes += minute_step
    new_hour = (next_minutes // 60) % 24
    new_minute = next_minutes % 60
    return dt.replace(hour=new_hour, minute=new_minute, second=0, microsecond=0)

# --- GESTION DE LA LANGUE ---
def set_language(lang_code):
    st.session_state.lang = lang_code

if 'lang' not in st.session_state:
    st.session_state.lang = 'fr'

with st.sidebar:
    st.header("Language / Langue")
    cols = st.columns(3)
    cols[0].button("🇬🇧", on_click=set_language, args=('en',), use_container_width=True)
    cols[1].button("🇫🇷", on_click=set_language, args=('fr',), use_container_width=True)
    cols[2].button("🇩🇪", on_click=set_language, args=('de',), use_container_width=True)

t = translations.get_translator(st.session_state.lang)

# --- INITIALISATION DU SESSION STATE ---
def init_session_state(lat=None, lon=None):
    if 'initialized' not in st.session_state:
        params = st.query_params.to_dict()
        history_from_url = params.get('history', "").split(',') if params.get('history') else []
        if history_from_url:
            st.session_state.history = history_from_url
            st.session_state.current_location = st.session_state.history[-1]
        else:
            initial_pos = find_closest_attraction(lat, lon)
            if lat and lon:
                st.toast(t("initial_pos_toast", pos=initial_pos), icon="📍")
            st.session_state.history = [initial_pos]
            st.session_state.current_location = initial_pos
        
        attractions_from_url_raw = params.get('attractions_to_visit', "")
        attractions_from_url = attractions_from_url_raw.split(',') if attractions_from_url_raw else []
        st.session_state.attractions_to_visit = attractions_from_url if attractions_from_url else mainCode.ATTRACTIONS_MASTER_LIST.copy()

        st.session_state.last_recommendation = None
        st.session_state.all_candidates = None
        st.session_state.virtual_line_active = False
        st.session_state.virtual_line_details = {}
        st.session_state.last_map_update_time = None 
        st.session_state.initialized = True
        update_url_state()

# --- FONCTIONS D'AFFICHAGE ---
def create_park_map(history, current_loc, recommendation, attractions_to_visit, vl_details, wait_times_data=None):
    coords = mainCode.ATTRACTIONS_COORDS
    points_to_show = set(attractions_to_visit)
    points_to_show.add(current_loc)
    if recommendation and recommendation['destination'] != "N/A":
        points_to_show.add(recommendation['destination'])
    if vl_details:
        points_to_show.add(vl_details['attraction'])

    valid_points = [loc for loc in points_to_show if loc in coords]
    if not valid_points:
        center_coords = (48.266, 7.721)
    else:
        avg_lat = sum(coords[loc][0] for loc in valid_points) / len(valid_points)
        avg_lon = sum(coords[loc][1] for loc in valid_points) / len(valid_points)
        center_coords = (avg_lat, avg_lon)

    m = folium.Map(location=center_coords, zoom_start=15, tiles="CartoDB positron")

    if len(history) > 1:
        path_coords = [coords[loc] for loc in history if loc in coords]
        if path_coords:
            folium.PolyLine(path_coords, color='blue', weight=4, opacity=0.8, tooltip=t("path_done")).add_to(m)

    if recommendation and recommendation['destination'] != "N/A":
        start_coord = coords.get(current_loc)
        end_coord = coords.get(recommendation['destination'])
        if start_coord and end_coord:
            folium.PolyLine([start_coord, end_coord], color='green', weight=5, dash_array='10', tooltip=t("next_step_header")).add_to(m)

    for name, location in coords.items():
        if name in points_to_show:
            style = "font-weight: bold; font-size: 11px; text-align: center; color: black;"
            bg_color = "background-color: rgba(255, 255, 255, 0.7);"
            html_content = f"<b>{name}</b>"
            
            if vl_details and name == vl_details['attraction']:
                popup_time = vl_details.get('time_str', vl_details.get('time', '').strftime('%H:%M'))
                html_content = f"<b>{name}</b><br>🎟️ VL: {popup_time}"
                bg_color = "background-color: rgba(255, 204, 203, 0.8);"
            elif name == current_loc:
                html_content = f"📍<b>{name}</b>"
                bg_color = "background-color: rgba(173, 216, 230, 0.8);"
            elif recommendation and name == recommendation['destination']:
                bg_color = "background-color: rgba(144, 238, 144, 0.8);"
            elif name in history:
                bg_color = "background-color: rgba(221, 160, 221, 0.8);"
            
            if wait_times_data and name in wait_times_data:
                wait_time = wait_times_data[name]
                if wait_time == "CLOSED":
                    wait_display = f"🔴 {t('closed')}"
                else:
                    wait_display = f"~{wait_time:.0f} {t('minutes_abbr')}"
                html_content += f"<br>{wait_display}"
            
            icon = DivIcon(
                icon_size=(130, 30),
                icon_anchor=(75, 18),
                html=f'<div style="{style} {bg_color} padding: 5px; border-radius: 5px; border: 1px solid black;">{html_content}</div>',
            )
            
            folium.Marker(
                location=location,
                icon=icon
            ).add_to(m)
            
    return m

def update_url_state():
    st.query_params["history"] = ",".join(st.session_state.history)
    st.query_params["attractions_to_visit"] = ",".join(st.session_state.attractions_to_visit)

def find_closest_attraction(user_lat, user_lon):
    if user_lat is None or user_lon is None: return START_LOCATION_DEFAULT
    return min(mainCode.ATTRACTIONS_COORDS.items(), 
               key=lambda item: (item[1][0] - user_lat)**2 + (item[1][1] - user_lon)**2)[0]

# --- DÉBUT DE L'INTERFACE PRINCIPALE ---
st.title(f"🎢 {t('app_title')}")


# --- GÉOLOCALISATION ET INITIALISATION ---
location_data = streamlit_geolocation()
user_lat = location_data.get('latitude') if location_data else None
user_lon = location_data.get('longitude') if location_data else None
init_session_state(user_lat, user_lon)

# --- MESSAGE D'ACCUEIL POUR LES NOUVEAUX UTILISATEURS ---
if 'welcome_dismissed' not in st.session_state:
    with st.container(border=True):
        st.header(t('welcome_header'))
        st.write(t('welcome_intro'))
        st.markdown(f"""
        - {t('welcome_step1')}
        - {t('welcome_step2')}
        - {t('welcome_step3')}
        """)
        if st.button(t('welcome_dismiss'), type="primary"):
            st.session_state.welcome_dismissed = True
            st.rerun()
    st.markdown("---")


# --- BARRE LATÉRALE (SIDEBAR) ---
with st.sidebar:
    st.markdown("---")
    st.header(t("support_header"))
    st.write(t("support_text"))
    st.link_button(t("support_button"), "https://www.buymeacoffee.com/nat4K", use_container_width=True)
    st.markdown("---")
    st.header(t("config_header"))
    
    selected_attractions = st.multiselect(
        t("attractions_select"), 
        options=mainCode.ATTRACTIONS_MASTER_LIST, 
        default=st.session_state.attractions_to_visit
    )
    if selected_attractions != st.session_state.attractions_to_visit:
        st.session_state.attractions_to_visit = selected_attractions
        update_url_state()
        st.rerun()
        
    st.markdown("---")
    st.info(t("start_pos_info", location=st.session_state.current_location))
    if st.button(f"🔄 {t('refresh_pos_button')}", help=t("refresh_pos_help")):
        if user_lat and user_lon:
            closest = find_closest_attraction(user_lat, user_lon)
            st.session_state.current_location = closest
            st.toast(t("pos_updated_toast", pos=closest), icon="🔄")
            st.rerun()
        else:
            st.error(t("geolocation_not_available_error"))
        
    st.markdown("---")
    
    with st.container(border=True):
        st.header(t("path_header"))
        if len(st.session_state.history) > 1:
            st.write(" ➡️ ".join(st.session_state.history))
        else:
            st.info(t("path_start_info"))

    st.markdown("---")
    if st.button(f"🗑️ {t('reset_day_button')}", use_container_width=True):
        keys_to_clear = list(st.session_state.keys())
        for key in keys_to_clear:
            del st.session_state[key]
        st.query_params.clear()
        st.rerun()

# --- STRUCTURE PRINCIPALE AVEC COLONNES ---
col_actions, col_map = st.columns([3, 2])

wait_times_info = {}
if st.session_state.all_candidates:
    wait_times_info = {c['destination']: c['real_wait_time'] for c in st.session_state.all_candidates}

with col_map:
    # Titre de la carte dynamique et propre
    if st.session_state.get("last_map_update_time"):
        update_time_str = st.session_state.last_map_update_time.strftime('%H:%M')
        map_title = t("map_header_with_time", time=update_time_str)
    else:
        map_title = t("map_header_base")
    st.header(map_title)

    park_map = create_park_map(
        history=st.session_state.history, 
        current_loc=st.session_state.current_location, 
        recommendation=st.session_state.last_recommendation, 
        attractions_to_visit=st.session_state.attractions_to_visit,
        vl_details=st.session_state.virtual_line_details if st.session_state.virtual_line_active else None,
        wait_times_data=wait_times_info
    )
    st_folium(park_map, width='100%', height=500, returned_objects=[])

with col_actions:
    st.header(t("actions_header"))

    with st.container(border=True):
        st.subheader(t("dashboard_header"))
        db_cols = st.columns(3)
        db_cols[0].metric(t("dashboard_done"), len(st.session_state.history) - 1)
        db_cols[1].metric(t("dashboard_remaining"), len(st.session_state.attractions_to_visit))
        vl_text = st.session_state.virtual_line_details.get('time_str', "Inactive") if st.session_state.virtual_line_active else "Inactive"
        db_cols[2].metric(t("dashboard_vl_active"), vl_text)

    if st.button(f"{t('find_best_button')}", type="primary", use_container_width=True):
        if not st.session_state.attractions_to_visit:
            st.warning(t("empty_list_warning"))
        else:
            with st.status(t('status_calculating'), expanded=True) as status:
                fuseau_horaire_parc = pytz.timezone('Europe/Berlin')
                now = datetime.now(fuseau_horaire_parc)
                st.session_state.last_map_update_time = now 
                vl_details = st.session_state.virtual_line_details if st.session_state.virtual_line_active else None
                
                status.update(label=t('status_fetching_wait_times'), state="running")
                recommendation, all_candidates = mainCode.find_best_next_step(
                    st.session_state.current_location, st.session_state.attractions_to_visit, now, vl_details
                )
                status.update(label=t('status_analyzing_paths'), state="running")
                st.session_state.last_recommendation = recommendation
                st.session_state.all_candidates = all_candidates

                if recommendation['cost'] == float('inf'):
                    st.session_state.last_recommendation = None
                
                status.update(label=t('status_done'), state="complete", expanded=False)
                st.rerun()

    with st.popover(f"{t('manage_vl_button')}", use_container_width=True):
        with st.form("virtual_line_form"):
            st.subheader(t("vl_popover_header"))
            vl_attraction_options = mainCode.VIRTUAL_LINE_ATTRACTIONS
            current_vl_attraction = st.session_state.virtual_line_details.get("attraction")
            index = vl_attraction_options.index(current_vl_attraction) if current_vl_attraction in vl_attraction_options else 0
            
            vl_attraction = st.selectbox(t("vl_attraction_select"), options=vl_attraction_options, index=index)
            
            fuseau_horaire_parc = pytz.timezone('Europe/Berlin')
            now = datetime.now(fuseau_horaire_parc)
            rounded_dt = round_up_time(now, minute_step=10)
            default_time = rounded_dt.time()

            if "time_only" in st.session_state.virtual_line_details:
                default_time = st.session_state.virtual_line_details["time_only"]

            vl_time = st.time_input(t("vl_time_input"), value=default_time)
            
            confirm_col, delete_col = st.columns([1,1])
            with confirm_col:
                if st.form_submit_button(t("vl_confirm_button"), use_container_width=True, type="primary"):
                    appointment_naive = datetime.combine(now.date(), vl_time)
                    appointment_tz = fuseau_horaire_parc.localize(appointment_naive)

                    if appointment_tz <= now:
                        appointment_tz += timedelta(days=1)

                    st.session_state.virtual_line_active = True
                    st.session_state.virtual_line_details = {
                        "attraction": vl_attraction, "time": appointment_tz,
                        "time_only": appointment_tz.time(), "time_str": appointment_tz.strftime('%H:%M'),
                        "timestamp": appointment_tz.timestamp()
                    }
                    st.toast(t("vl_set_toast", attraction=vl_attraction, time=appointment_tz.strftime('%H:%M')), icon="✅")
                    st.rerun()
            with delete_col:
                if st.form_submit_button(t("vl_delete_button"), use_container_width=True):
                    st.session_state.virtual_line_active = False
                    st.session_state.virtual_line_details = {}
                    st.session_state.last_recommendation = None
                    st.session_state.all_candidates = None
                    st.toast(t("vl_cancelled_toast"), icon="❌")
                    st.rerun()

    if st.session_state.last_recommendation:
        rec = st.session_state.last_recommendation
        with st.container(border=True):
            if rec['cost'] == float('inf'):
                 st.error(t("no_attraction_possible"))
            else:
                st.success(t("suggested_destination", destination=rec['destination']))
                sub_col1, sub_col2 = st.columns(2)
                real_wait = rec['real_wait_time']
                wait_display = f"🔴 {t('closed')}" if real_wait == "CLOSED" else f"~{real_wait:.0f} {t('minutes_abbr')}"
                sub_col1.metric(f"🚶 {t('travel_metric')}", f"~{rec['travel_time']:.0f} {t('minutes_abbr')}")
                sub_col2.metric(f"⏳ {t('wait_metric')}", wait_display)
                
                if st.button(f"✅ {t('done_button', destination=rec['destination'])}", use_container_width=True):
                    last_done = rec['destination']
                    st.session_state.history.append(last_done)
                    st.session_state.current_location = last_done
                    if last_done in st.session_state.attractions_to_visit:
                        st.session_state.attractions_to_visit.remove(last_done)
                    st.session_state.last_recommendation = None
                    st.session_state.all_candidates = None
                    update_url_state()
                    st.rerun()

    elif st.session_state.all_candidates and st.session_state.all_candidates[0]['cost'] == float('inf'):
         st.error(t("no_attraction_possible"))

    if st.session_state.all_candidates:
        with st.expander(f"{t('show_details_expander')}", expanded=False):
            for candidate in st.session_state.all_candidates:
                is_late = candidate.get('is_late', False)
                if is_late:
                    st.markdown("<div style='opacity: 0.5;'>", unsafe_allow_html=True)

                st.markdown(f"--- \n**{t('candidate_header', destination=candidate['destination'])}**")
                
                cols = st.columns(4)
                
                cols[0].metric(t("travel_details"), f"{candidate['travel_time']:.0f} {t('minutes_abbr')}")

                real_wait = candidate['real_wait_time']
                predicted_wait = candidate['predicted_wait_time']
                delta_value = None
                if real_wait == "CLOSED":
                    metric_value = t("closed")
                else:
                    predicted_display = f"{predicted_wait:.0f}" if isinstance(predicted_wait, (int, float)) else t("not_applicable_abbr")
                    metric_value = f"{real_wait:.0f} / {predicted_display} {t('minutes_abbr')}"
                    if isinstance(predicted_wait, (int, float)) and real_wait != "CLOSED":
                        diff = real_wait - predicted_wait
                        delta_value = f"{diff:+.0f}"
                cols[1].metric(t("wait_details"), metric_value, delta=delta_value, delta_color="inverse")
                
                if st.session_state.virtual_line_active:
                    arrival_time_vl = candidate.get('arrival_at_vl')
                    arrival_display = arrival_time_vl.strftime('%H:%M') if isinstance(arrival_time_vl, datetime) else t("not_applicable_abbr")
                    cols[2].metric(t("end_time_vl_details"), arrival_display, help="Heure d'arrivée estimée à l'attraction en Virtual Line")
                else:
                    end_time = candidate.get('end_time')
                    end_time_display = end_time.strftime('%H:%M') if isinstance(end_time, datetime) else t("not_applicable_abbr")
                    cols[2].metric(t("end_time_details"), end_time_display)

                cost_display = f"{candidate['cost']:.2f}" if candidate['cost'] != float('inf') else "🚫"
                cols[3].metric(t("cost_details"), cost_display, help="Score de priorité (plus bas = mieux)")
                
                if candidate['cost'] != float('inf'):
                    if st.button(t('choose_this_attraction'), key=f"done_candidate_{candidate['destination']}", use_container_width=True):
                        last_done = candidate['destination']
                        st.session_state.history.append(last_done)
                        st.session_state.current_location = last_done
                        if last_done in st.session_state.attractions_to_visit:
                            st.session_state.attractions_to_visit.remove(last_done)
                        st.session_state.last_recommendation = None
                        st.session_state.all_candidates = None
                        update_url_state()
                        st.rerun()

                if is_late:
                    st.markdown("</div>", unsafe_allow_html=True)

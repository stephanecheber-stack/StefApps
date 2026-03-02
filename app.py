# -*- coding: utf-8 -*-
import streamlit as st
import requests
import pandas as pd
import os
from dotenv import load_dotenv
from flow_components import show_flow_designer
from engine import normalize_status

# Load Environment Variables
load_dotenv()

# Configuration
API_URL = "http://localhost:8000"
WORKFLOWS_FILE = "workflows.yaml"
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "IMPOSSIBLE_PASSWORD_SEQUENCE_XYZ")

# -----------------------------------------------------------------------------
# LOGIQUE DE DONNÉES
# -----------------------------------------------------------------------------

def fetch_groups_from_api():
    try:
        resp = requests.get(f"{API_URL}/groups/", timeout=3)
        if resp.status_code == 200:
            return [g['name'] for g in resp.json()]
    except: pass
    return ["Non assigné"]

def refresh_groups():
    st.session_state["support_groups"] = fetch_groups_from_api()

def init_state():
    if "authenticated" not in st.session_state: st.session_state.authenticated = False
    if "delete_confirm_check" not in st.session_state: st.session_state.delete_confirm_check = False
    if "skip_workflow" not in st.session_state: st.session_state["skip_workflow"] = True
    if "support_groups" not in st.session_state: st.session_state["support_groups"] = fetch_groups_from_api()
    if "grid_nonce" not in st.session_state: st.session_state.grid_nonce = 0
    if "active_kpi_filter" not in st.session_state: st.session_state.active_kpi_filter = "Total"
    
    if "create_title" not in st.session_state: st.session_state.create_title = ""
    if "create_desc" not in st.session_state: st.session_state.create_desc = ""
    if "create_priority" not in st.session_state: st.session_state.create_priority = "Moyenne"
    if "create_assigned" not in st.session_state: st.session_state.create_assigned = "Non assigné"

# -----------------------------------------------------------------------------
# CALLBACKS
# -----------------------------------------------------------------------------

def cb_set_kpi_filter(filter_name):
    if st.session_state.active_kpi_filter == filter_name and filter_name != "Total":
        st.session_state.active_kpi_filter = "Total"
    else:
        st.session_state.active_kpi_filter = filter_name

def cb_create_task():
    if not st.session_state.create_title:
        st.toast("❌ Le titre est obligatoire.", icon="🚨")  # FIX #5 : st.error() invisible dans les callbacks
        return
    payload = {
        "title": st.session_state.create_title, "description": st.session_state.create_desc,
        "priority": st.session_state.create_priority, "assigned_to": st.session_state.create_assigned
    }
    try:
        if requests.post(f"{API_URL}/tasks/", json=payload, timeout=5).status_code == 200:
            st.session_state.create_title = ""; st.session_state.create_desc = ""
            st.toast("✅ Ticket créé")
    except requests.exceptions.RequestException as e:  # FIX OBS #3 : except typé
        st.toast(f"❌ Erreur API : {e}", icon="🚨")

def cb_update_task_dashboard(task_id):
    payload = {
        "title": st.session_state[f"edit_title_{task_id}"], "status": st.session_state[f"edit_status_{task_id}"],
        "priority": st.session_state[f"edit_priority_{task_id}"], "assigned_to": st.session_state[f"edit_assign_{task_id}"],
        "description": st.session_state[f"edit_desc_{task_id}"], "tags": st.session_state.get(f"edit_tags_{task_id}", "")
    }
    try:
        if requests.put(f"{API_URL}/tasks/{task_id}", json=payload, timeout=5).status_code == 200:  # FIX #3 : timeout
            st.toast("✅ Modifications enregistrées")
    except requests.exceptions.RequestException as e:  # FIX OBS #3 : except typé
        st.toast(f"❌ Erreur mise à jour : {e}", icon="🚨")

# -----------------------------------------------------------------------------
# STYLE CSS FINAL (HAUTE VISIBILITÉ)
# -----------------------------------------------------------------------------

st.set_page_config(page_title="LiteFlow Pro", layout="wide", page_icon="⚡")
init_state()

st.markdown("""
<style>
    /* Fond Cloud */
    .stApp { background-color: #f1f5f9; }

    /* Sidebar Navy */
    section[data-testid="stSidebar"] { background-color: #0f172a !important; }
    section[data-testid="stSidebar"] label, section[data-testid="stSidebar"] h1 { color: white !important; }

    /* STYLE GÉNÉRAL DES BOUTONS KPI */
    .kpi-btn-container .stButton > button {
        height: 100px !important;
        width: 100% !important;
        border-radius: 12px !important;
        font-size: 1.1rem !important;
        font-weight: 700 !important;
        color: #ffffff !important;
        border: none !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1) !important;
        white-space: pre-wrap !important; /* Permet le retour à la ligne */
    }

    /* INACTIF : BLEU MARINE PROCHÉ SIDEBAR */
    .kpi-inactive .stButton > button {
        background-color: #0f172a !important;
    }
    .kpi-inactive .stButton > button:hover {
        background-color: #1e293b !important;
    }

    /* ACTIF : VERT FONCÉ ACTION */
    .kpi-active .stButton > button {
        background-color: #064e3b !important;
        border: 2px solid #10b981 !important;
    }

    /* Conteneurs Blancs */
    [data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #ffffff !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 12px !important;
    }
</style>
""", unsafe_allow_html=True)

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("# ⚡ LiteFlow Pro")
    if not st.session_state.authenticated:
        pwd = st.text_input("Accès Admin", type="password")
        if st.button("DÉVERROUILLER"):
            if pwd == ADMIN_PASSWORD:
                st.session_state.authenticated = True; st.rerun()
    else:
        st.success("Administrateur")
        if st.button("QUITTER"): st.session_state.authenticated = False; st.rerun()
    st.divider()
    st.markdown("### 🚀 CRÉATION")
    st.text_input("Titre", key="create_title")
    st.text_area("Description", key="create_desc", height=80)  # FIX #6 : champ description manquant
    st.selectbox("Priorité", ["Basse", "Moyenne", "Haute", "Critique"], key="create_priority")
    st.selectbox("Assigné à", st.session_state["support_groups"], key="create_assigned")
    st.button("OUVRIR LE TICKET", on_click=cb_create_task, type="secondary")

# --- MAIN DASHBOARD ---
st.title("📑 Dashboard Opérationnel")
tabs = st.tabs(["📋 Liste", "⚡ Flow Designer", "🗄️ Base de données", "🛠️ Admin"])

with tabs[0]:
    try:
        resp = requests.get(f"{API_URL}/tasks/?limit=1000", timeout=5)  # FIX #3 : timeout ajouté
        if resp.status_code == 200:
            all_data = resp.json()
            df_base = pd.DataFrame(all_data) if all_data else pd.DataFrame()
            
            # Calculs
            total_n = len(df_base)
            res_n = len(df_base[df_base['status'] == 'Terminé']) if not df_base.empty else 0
            pend_n = total_n - res_n
            
            # KPI DYNAMIQUES
            k1, k2, k3 = st.columns(3)
            
            with k1:
                active = st.session_state.active_kpi_filter == "Total"
                st.markdown(f'<div class="{"kpi-active" if active else "kpi-inactive"} kpi-btn-container">', unsafe_allow_html=True)
                st.button(f"📊 {total_n}\nTICKETS TOTAUX", on_click=cb_set_kpi_filter, args=("Total",), key="k_tot")
                st.markdown('</div>', unsafe_allow_html=True)

            with k2:
                active = st.session_state.active_kpi_filter == "Clotures"
                st.markdown(f'<div class="{"kpi-active" if active else "kpi-inactive"} kpi-btn-container">', unsafe_allow_html=True)
                st.button(f"✅ {res_n}\nCLÔTURÉS", on_click=cb_set_kpi_filter, args=("Clotures",), key="k_res")
                st.markdown('</div>', unsafe_allow_html=True)

            with k3:
                active = st.session_state.active_kpi_filter == "Attente"
                st.markdown(f'<div class="{"kpi-active" if active else "kpi-inactive"} kpi-btn-container">', unsafe_allow_html=True)
                st.button(f"⏳ {pend_n}\nEN ATTENTE", on_click=cb_set_kpi_filter, args=("Attente",), key="k_pend")
                st.markdown('</div>', unsafe_allow_html=True)

            # Logique de Filtrage
            f_data = all_data
            if st.session_state.active_kpi_filter == "Clotures":
                f_data = [t for t in f_data if t['status'] == 'Terminé']
            elif st.session_state.active_kpi_filter == "Attente":
                f_data = [t for t in f_data if t['status'] != 'Terminé']
            
            st.divider()
            search = st.text_input("Recherche rapide", placeholder="Filtrer...", label_visibility="collapsed")
            if search:
                f_data = [t for t in f_data if any(search.lower() in str(v).lower() for v in t.values())]

            if f_data:
                df = pd.DataFrame(f_data)
                status_map = {"Nouveau": "🔵 Nouveau", "À faire": "🟡 À faire", "En cours": "🟢 En cours", "Terminé": "⚪ Terminé"}
                df['status_view'] = df['status'].apply(lambda x: status_map.get(normalize_status(x), x))
                
                sel = st.dataframe(df[['id', 'title', 'status_view', 'priority', 'assigned_to']], width='stretch', hide_index=True, on_select="rerun", selection_mode="single-row", key=f"grid_{st.session_state.grid_nonce}")

                if sel and len(sel.selection.rows) > 0:
                    t = df.iloc[list(sel.selection.rows)[0]]
                    st.markdown(f"### 🔎 Édition Ticket #{t['id']}")
                    # FIX #1 & #2 : clé corrigée (edit_t_ → edit_title_) + widgets manquants ajoutés
                    with st.container(border=True):
                        col_a, col_b = st.columns(2)
                        STATUS_OPTS = ["Nouveau", "À faire", "En cours", "Terminé"]
                        PRIORITY_OPTS = ["Basse", "Moyenne", "Haute", "Critique"]
                        col_a.text_input("Titre", value=t.get('title', ''), key=f"edit_title_{t['id']}")
                        try:
                            status_idx = STATUS_OPTS.index(t.get('status', 'Nouveau'))
                        except ValueError:
                            status_idx = 0
                        col_b.selectbox("Statut", STATUS_OPTS, index=status_idx, key=f"edit_status_{t['id']}")
                        col_c, col_d = st.columns(2)
                        try:
                            priority_idx = PRIORITY_OPTS.index(t.get('priority', 'Moyenne'))
                        except ValueError:
                            priority_idx = 1
                        col_c.selectbox("Priorité", PRIORITY_OPTS, index=priority_idx, key=f"edit_priority_{t['id']}")
                        try:
                            assign_idx = st.session_state['support_groups'].index(t.get('assigned_to', ''))
                        except (ValueError, KeyError):
                            assign_idx = 0
                        col_d.selectbox("Assigné à", st.session_state['support_groups'], index=assign_idx, key=f"edit_assign_{t['id']}")
                        st.text_area("Description", value=t.get('description', ''), key=f"edit_desc_{t['id']}")
                        st.button("💾 ENREGISTRER", type="primary", on_click=cb_update_task_dashboard, args=(t['id'],))
            else:
                st.info("Aucun ticket.")
    except requests.exceptions.RequestException as e:  # FIX OBS #3 : except typé
        st.error(f"❌ Connexion API impossible : {e}")
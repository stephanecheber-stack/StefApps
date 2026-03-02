# -*- coding: utf-8 -*-
import streamlit as st
import requests
import pandas as pd
import time
import os
from dotenv import load_dotenv
from flow_components import show_flow_designer
from engine import normalize_status

# --- CONFIGURATION & SÉCURITÉ ---
load_dotenv()
API_URL = os.getenv("API_URL", "http://localhost:8000")
WORKFLOWS_FILE = "workflows.yaml"
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "IMPOSSIBLE_PASSWORD_SEQUENCE_XYZ")

# -----------------------------------------------------------------------------
# LOGIQUE DE DONNÉES (SESSION & API)
# -----------------------------------------------------------------------------

def fetch_groups():
    try:
        resp = requests.get(f"{API_URL}/groups/", timeout=3)
        if resp.status_code == 200:
            return [g['name'] for g in resp.json()]
    except: pass
    return ["Non assigné"]

def init_state():
    """Initialisation du moteur d'état Streamlit."""
    if "authenticated" not in st.session_state: st.session_state.authenticated = False
    if "active_kpi_filter" not in st.session_state: st.session_state.active_kpi_filter = "Total"
    if "grid_nonce" not in st.session_state: st.session_state.grid_nonce = 0
    if "support_groups" not in st.session_state: st.session_state["support_groups"] = fetch_groups()
    
    # Formulaires
    fields = ["create_title", "create_desc", "create_tags", "new_group_name"]
    for f in fields:
        if f not in st.session_state: st.session_state[f] = ""
    if "create_priority" not in st.session_state: st.session_state.create_priority = "Moyenne"

# -----------------------------------------------------------------------------
# CALLBACKS (Standard Architecte : Pas de st.rerun interne)
# -----------------------------------------------------------------------------

def cb_set_kpi(filter_name):
    st.session_state.active_kpi_filter = "Total" if st.session_state.active_kpi_filter == filter_name and filter_name != "Total" else filter_name

def cb_create_task():
    if not st.session_state.create_title:
        st.error("Titre obligatoire"); return
    payload = {
        "title": st.session_state.create_title,
        "description": st.session_state.create_desc,
        "priority": st.session_state.create_priority,
        "assigned_to": st.session_state.get("create_assigned", "Non assigné")
    }
    try:
        if requests.post(f"{API_URL}/tasks/", json=payload).status_code == 200:
            st.session_state.create_title = ""; st.session_state.create_desc = ""
            st.toast("✅ Ticket créé !")
    except: st.error("Erreur API")

def cb_update_task(tid):
    payload = {
        "title": st.session_state[f"edit_t_{tid}"],
        "status": st.session_state[f"edit_s_{tid}"],
        "priority": st.session_state[f"edit_p_{tid}"],
        "assigned_to": st.session_state[f"edit_a_{tid}"],
        "description": st.session_state[f"edit_d_{tid}"]
    }
    try:
        if requests.put(f"{API_URL}/tasks/{tid}", json=payload).status_code == 200:
            st.toast("✅ Mis à jour")
    except: st.error("Erreur")

def cb_delete_task(tid):
    try:
        if requests.delete(f"{API_URL}/tasks/{tid}").status_code == 200:
            st.session_state.grid_nonce += 1
            st.toast("🗑️ Supprimé")
    except: st.error("Erreur")

def cb_group_action(action, name=None, gid=None):
    try:
        if action == "add":
            requests.post(f"{API_URL}/groups/", json={"name": name})
            st.session_state.new_group_name = ""
        elif action == "del":
            requests.delete(f"{API_URL}/groups/{gid}")
        st.session_state["support_groups"] = fetch_groups()
        st.toast(f"✅ Groupe mis à jour")
    except: st.error("Erreur Base de données")

# -----------------------------------------------------------------------------
# INTERFACE & STYLE CSS (CIBLAGE DIRECT DATA-TESTID)
# -----------------------------------------------------------------------------

st.set_page_config(page_title="LiteFlow Pro", layout="wide", page_icon="⚡")
init_state()

st.markdown("""
<style>
    /* Global & Sidebar */
    .stApp { background-color: #f1f5f9; }
    section[data-testid="stSidebar"] { background-color: #0f172a !important; }
    section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] label, .sidebar-title { color: white !important; font-weight: 800 !important; }
    h1, h2, h3 { color: #0f172a !important; font-weight: 700 !important; }

    /* BOUTONS SECONDAIRES (Standard / Inactif) -> BLEU SAAS */
    button[data-testid="stBaseButton-secondary"] {
        background-color: #2563eb !important;
        color: white !important;
        border: none !important;
        font-weight: 700 !important;
        height: 3rem !important;
    }

    /* BOUTONS PRIMAIRES (KPI Actif) -> VERT FONCÉ */
    button[data-testid="stBaseButton-primary"] {
        background-color: #064e3b !important;
        color: white !important;
        border: 2px solid #10b981 !important;
        font-weight: 800 !important;
        height: 3rem !important;
    }

    /* Cards KPI (Conteneurs) */
    .kpi-card { background-color: #0f172a; border-radius: 12px; padding: 20px; color: white; min-height: 100px; margin-bottom: 10px; }
    
    /* Conteneurs Blancs */
    [data-testid="stVerticalBlockBorderWrapper"] { background-color: #ffffff !important; border: 1px solid #e2e8f0 !important; border-radius: 12px !important; }
</style>
""", unsafe_allow_html=True)

# --- BARRE LATÉRALE ---
with st.sidebar:
    st.markdown("# ⚡ LiteFlow Pro")
    if not st.session_state.authenticated:
        pwd = st.text_input("Code Admin", type="password")
        if st.button("DÉVERROUILLER", type="secondary"):
            if pwd == ADMIN_PASSWORD:
                st.session_state.authenticated = True; st.rerun()
    else:
        st.success("Admin Connecté")
        if st.button("QUITTER", type="secondary"): st.session_state.authenticated = False; st.rerun()

    st.divider()
    st.markdown('<p class="sidebar-title">CRÉATION</p>', unsafe_allow_html=True)
    st.text_input("Titre", key="create_title")
    st.text_area("Description", key="create_desc", height=100)
    st.selectbox("Priorité", ["Basse", "Moyenne", "Haute", "Critique"], key="create_priority")
    st.selectbox("Assignation", st.session_state["support_groups"], key="create_assigned")
    st.button("OUVRIR LE TICKET", on_click=cb_create_task, type="secondary")

# --- NAVIGATION ---
st.title("📑 Dashboard Opérationnel")
tabs = st.tabs(["📋 Dashboard", "⚡ Flow Designer", "🗄️ Base de données", "🛠️ Admin Tools"])

# --- TAB 1 : DASHBOARD ---
with tabs[0]:
    try:
        resp = requests.get(f"{API_URL}/tasks/?limit=1000")
        if resp.status_code == 200:
            data = resp.json()
            df = pd.DataFrame(data) if data else pd.DataFrame()
            
            # KPI ROW
            k1, k2, k3 = st.columns(3)
            tot, res = len(df), len(df[df['status'] == 'Terminé']) if not df.empty else 0
            
            with k1: st.button(f"📊 {tot}\nTOTAL", on_click=cb_set_kpi, args=("Total",), type="primary" if st.session_state.active_kpi_filter == "Total" else "secondary", use_container_width=True)
            with k2: st.button(f"✅ {res}\nCLÔTURÉS", on_click=cb_set_kpi, args=("Clotures",), type="primary" if st.session_state.active_kpi_filter == "Clotures" else "secondary", use_container_width=True)
            with k3: st.button(f"⏳ {tot-res}\nEN ATTENTE", on_click=cb_set_kpi, args=("Attente",), type="primary" if st.session_state.active_kpi_filter == "Attente" else "secondary", use_container_width=True)

            # Filtrage
            f_data = data
            if st.session_state.active_kpi_filter == "Clotures": f_data = [t for t in data if t['status'] == 'Terminé']
            elif st.session_state.active_kpi_filter == "Attente": f_data = [t for t in data if t['status'] != 'Terminé']
            
            st.divider()
            if f_data:
                df_view = pd.DataFrame(f_data)
                df_view['status'] = df_view['status'].apply(normalize_status)
                sel = st.dataframe(df_view[['id', 'title', 'status', 'priority', 'assigned_to']], width='stretch', hide_index=True, on_select="rerun", selection_mode="single-row", key=f"g_{st.session_state.grid_nonce}")

                if sel and len(sel.selection.rows) > 0:
                    t = f_data[list(sel.selection.rows)[0]]; tid = t['id']
                    st.markdown(f"### 🔎 Édition Ticket #{tid}")
                    with st.container(border=True):
                        c1, c2 = st.columns(2)
                        st_list = ["Nouveau", "À faire", "En cours", "Terminé"]
                        c1.text_input("Titre", value=t['title'], key=f"edit_t_{tid}")
                        c1.selectbox("Statut", st_list, index=st_list.index(normalize_status(t['status'])), key=f"edit_s_{tid}")
                        c2.selectbox("Priorité", ["Basse", "Moyenne", "Haute", "Critique"], index=["Basse", "Moyenne", "Haute", "Critique"].index(t['priority']), key=f"edit_p_{tid}")
                        c2.selectbox("Groupe", st.session_state["support_groups"], index=st.session_state["support_groups"].index(t['assigned_to']) if t['assigned_to'] in st.session_state["support_groups"] else 0, key=f"edit_a_{tid}")
                        st.text_area("Description", value=t.get('description', ""), key=f"edit_d_{tid}")
                        colb1, colb2 = st.columns([1, 4])
                        colb1.button("💾 SAUVEGARDER", type="secondary", on_click=cb_update_task, args=(tid,))
                        if st.session_state.authenticated:
                            colb2.button("🗑️ SUPPRIMER", type="secondary", on_click=cb_delete_task, args=(tid,))
            else: st.info("Aucun ticket.")
    except: st.error("API déconnectée.")

# --- TAB 3 : BASE DE DONNÉES ---
with tabs[2]:
    if st.session_state.authenticated:
        st.header("🗄️ Groupes de Support")
        with st.container(border=True):
            cin, cbt = st.columns([3, 1])
            cin.text_input("Nouveau groupe", key="new_group_name")
            cbt.button("AJOUTER", on_click=lambda: cb_group_action("add", name=st.session_state.new_group_name), type="secondary")
        
        try:
            grs = requests.get(f"{API_URL}/groups/").json()
            if grs:
                st.dataframe(pd.DataFrame(grs)[['id', 'name']], width='stretch', hide_index=True)
                g_del = st.selectbox("Supprimer un groupe", options=grs, format_func=lambda x: x['name'])
                st.button("SUPPRIMER SÉLECTION", on_click=lambda: cb_group_action("del", gid=g_del['id']), type="secondary")
        except: pass
    else: st.warning("🔐 Accès Admin requis")

# --- TAB 4 : ADMIN TOOLS ---
with tabs[3]:
    if st.session_state.authenticated:
        st.header("🛠️ Maintenance")
        with st.container(border=True):
            st.subheader("📜 Logs d'Audit")
            try:
                logs = requests.get(f"{API_URL}/audit/logs").json()
                if logs: st.dataframe(pd.DataFrame(logs).sort_values('id', ascending=False), width='stretch', hide_index=True)
            except: st.error("Erreur Logs")
        
        if st.button("💾 GÉNÉRER BACKUP DB", type="secondary"):
            try:
                b = requests.get(f"{API_URL}/backup")
                st.download_button("📥 TÉLÉCHARGER", b.content, "backup.db", type="secondary")
            except: st.error("Erreur Backup")
    else: st.warning("🔐 Accès Admin requis")

# --- TAB 2 : FLOW DESIGNER ---
with tabs[1]:
    if st.session_state.authenticated: show_flow_designer(API_URL, WORKFLOWS_FILE, st.session_state["support_groups"])
    else: st.warning("🔐 Accès Admin requis")
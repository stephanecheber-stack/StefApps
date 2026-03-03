# -*- coding: utf-8 -*-
import streamlit as st
import requests
import pandas as pd
import time
import os
from datetime import datetime
from dotenv import load_dotenv
from flow_components import show_flow_designer
from engine import normalize_status

# --- CONFIGURATION & SÉCURITÉ ---
load_dotenv()
API_URL = os.getenv("API_URL", "http://localhost:8000")
WORKFLOWS_FILE = "workflows.yaml"
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "IMPOSSIBLE_PASSWORD_SEQUENCE_XYZ")

# -----------------------------------------------------------------------------
# LOGIQUE DE DONNÉES
# -----------------------------------------------------------------------------

def fetch_data(endpoint):
    try:
        resp = requests.get(f"{API_URL}/{endpoint}/", timeout=5)
        return resp.json() if resp.status_code == 200 else []
    except: return []

def init_state():
    """Initialisation du moteur d'état."""
    if "authenticated" not in st.session_state: st.session_state.authenticated = False
    if "active_filter" not in st.session_state: st.session_state.active_filter = "Total"
    if "grid_nonce" not in st.session_state: st.session_state.grid_nonce = 0
    
    # Données de fondation
    if "classifications" not in st.session_state: st.session_state["classifications"] = fetch_data("classifications")
    if "support_groups" not in st.session_state: st.session_state["support_groups"] = fetch_data("groups")
    if "non_assigne" not in st.session_state: st.session_state["non_assigne"] = {"id": None, "name": "Non assigné"}

    # Formulaires
    for f in ["create_title", "create_desc", "new_group_name"]:
        if f not in st.session_state: st.session_state[f] = ""
    if "create_priority" not in st.session_state: st.session_state.create_priority = "Moyenne"

# -----------------------------------------------------------------------------
# CALLBACKS
# -----------------------------------------------------------------------------

def cb_set_filter(name):
    st.session_state.active_filter = "Total" if st.session_state.active_filter == name and name != "Total" else name

def cb_create_task():
    if not st.session_state.create_title:
        st.error("Titre obligatoire"); return
    payload = {
        "title": st.session_state.create_title,
        "description": st.session_state.create_desc,
        "priority": st.session_state.create_priority,
        "assigned_to": st.session_state.create_assigned['name'] if isinstance(st.session_state.get("create_assigned"), dict) else "Non assigné",
        "classification_id": st.session_state.create_classif.get('id') if st.session_state.get("create_classif") else None
    }
    try:
        if requests.post(f"{API_URL}/tasks/", json=payload).status_code == 200:
            st.session_state.create_title = ""; st.session_state.create_desc = ""
            st.toast("✅ Ticket enregistré")
    except: st.error("Erreur API")

def cb_update_task(tid):
    payload = {
        "title": st.session_state[f"edit_t_{tid}"],
        "status": st.session_state[f"edit_s_{tid}"],
        "priority": st.session_state[f"edit_p_{tid}"],
        "assigned_to": st.session_state[f"edit_a_{tid}"]['name'] if isinstance(st.session_state.get(f"edit_a_{tid}"), dict) else "Non assigné",
        "description": st.session_state[f"edit_d_{tid}"],
        "classification_id": st.session_state[f"edit_c_{tid}"].get('id') if st.session_state.get(f"edit_c_{tid}") else None
    }
    try:
        if requests.put(f"{API_URL}/tasks/{tid}", json=payload).status_code == 200:
            st.toast("✅ Modifications enregistrées")
    except: st.error("Erreur")

def cb_delete_task(tid):
    try:
        if requests.delete(f"{API_URL}/tasks/{tid}").status_code == 200:
            st.session_state.grid_nonce += 1
            st.toast("🗑️ Ticket supprimé")
    except: st.error("Erreur")

def cb_group_action(action, name=None, gid=None):
    try:
        if action == "add":
            if requests.post(f"{API_URL}/groups/", json={"name": name}).status_code == 200:
                st.toast(f"✅ Groupe {name} ajouté")
        elif action == "del":
            if requests.delete(f"{API_URL}/groups/{gid}").status_code == 200:
                st.toast("🗑️ Groupe supprimé")
    except: st.error("Erreur API")

# -----------------------------------------------------------------------------
# DESIGN CSS
# -----------------------------------------------------------------------------

st.set_page_config(page_title="LiteFlow Pro", layout="wide", page_icon="⚡")
init_state()

st.markdown("""
<style>
    .stApp { background-color: #f1f5f9; }
    section[data-testid="stSidebar"] { background-color: #0f172a !important; }
    section[data-testid="stSidebar"] label, .sidebar-header { color: white !important; font-weight: 800 !important; }
    h1, h2, h3 { color: #0f172a !important; font-weight: 700 !important; }

    /* BOUTONS SECONDAIRES (Bleu SaaS) */
    button[data-testid="stBaseButton-secondary"] {
        background-color: #2563eb !important;
        color: white !important;
        border: none !important;
        font-weight: 700 !important;
    }

    /* BOUTONS PRIMAIRES (Vert Foncé) */
    button[data-testid="stBaseButton-primary"] {
        background-color: #064e3b !important;
        color: white !important;
        border: 2px solid #10b981 !important;
        font-weight: 800 !important;
    }

    [data-testid="stVerticalBlockBorderWrapper"] { background-color: #ffffff !important; border: 1px solid #e2e8f0 !important; border-radius: 12px !important; }
</style>
""", unsafe_allow_html=True)

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("<h1 style='color:white;'>⚡ LiteFlow Pro</h1>", unsafe_allow_html=True)
    if not st.session_state.authenticated:
        pwd = st.text_input("Code Admin", type="password")
        if st.button("DÉVERROUILLER", type="secondary", width='stretch'):
            if pwd == ADMIN_PASSWORD: st.session_state.authenticated = True; st.rerun()
    else:
        st.success("Admin Connecté")
        if st.button("QUITTER", type="secondary", width='stretch'): st.session_state.authenticated = False; st.rerun()

    st.divider()
    st.markdown('<p class="sidebar-header">CRÉATION</p>', unsafe_allow_html=True)
    st.text_input("Titre", key="create_title")
    st.text_area("Description", key="create_desc", height=100)
    
    classifs = st.session_state["classifications"]
    nature = st.selectbox("Nature", options=classifs, format_func=lambda x: x['name'], key="create_classif")
    
    valid_groups = [g for g in st.session_state["support_groups"] if any(c['id'] == nature['id'] for c in g.get('classifications', []))] if nature else []
    st.selectbox("Assignation", options=[st.session_state["non_assigne"]] + valid_groups, format_func=lambda x: x['name'], key="create_assigned")
    
    st.selectbox("Priorité", ["Basse", "Moyenne", "Haute", "Critique"], key="create_priority")
    st.button("OUVRIR LE TICKET", on_click=cb_create_task, type="secondary", width='stretch')

# --- MAIN ---
st.title("📑 Dashboard Opérationnel")
tabs = st.tabs(["📋 Dashboard", "⚡ Flow Designer", "🗄️ Base de données", "🛠️ Admin Tools"])

with tabs[0]:
    try:
        tasks = fetch_data("tasks")
        if tasks:
            # 1. KPIs
            df_full = pd.DataFrame(tasks)
            tot, res = len(df_full), len(df_full[df_full['status'] == 'Terminé'])
            k1, k2, k3 = st.columns(3)
            with k1: st.button(f"📊 {tot}\nTOTAL", on_click=cb_set_filter, args=("Total",), type="primary" if st.session_state.active_filter == "Total" else "secondary", use_container_width=True)
            with k2: st.button(f"✅ {res}\nCLÔTURÉS", on_click=cb_set_filter, args=("Clotures",), type="primary" if st.session_state.active_filter == "Clotures" else "secondary", use_container_width=True)
            with k3: st.button(f"⏳ {tot-res}\nEN ATTENTE", on_click=cb_set_filter, args=("Attente",), type="primary" if st.session_state.active_filter == "Attente" else "secondary", use_container_width=True)

            # 2. Barre de recherche
            with st.container(border=True):
                c_r, c_s = st.columns([1, 4])
                with c_r: st.button("🔄 ACTUALISER", type="secondary", width='stretch', key="ref_dash")
                with c_s: search = st.text_input("Recherche", placeholder="Filtrer ID, Titre, Nature, Description...", label_visibility="collapsed", key="search_input")

            # 3. Filtrage Logique
            f_tasks = tasks
            if st.session_state.active_filter == "Clotures": f_tasks = [t for t in tasks if t['status'] == 'Terminé']
            elif st.session_state.active_filter == "Attente": f_tasks = [t for t in tasks if t['status'] != 'Terminé']
            
            if search:
                q = search.lower()
                f_tasks = [t for t in f_tasks if any(q in str(v).lower() for v in t.values())]

            # 4. Préparation et Rendu de la Grille
            if f_tasks:
                df_v = pd.DataFrame(f_tasks)
                
                # Formatage des colonnes (RESTAURATION)
                df_v['status'] = df_v['status'].apply(normalize_status)
                df_v['Nature'] = df_v['classification_name'].apply(lambda x: f"🛠️ {x}" if x == "Incidents" else f"📝 {x}")
                df_v['Parent'] = df_v['parent_id'].apply(lambda x: int(x) if pd.notnull(x) else "")
                df_v['Ouvert le'] = pd.to_datetime(df_v['created_at']).dt.strftime('%d/%m/%Y %H:%M')
                df_v['Terminé le'] = pd.to_datetime(df_v['closed_at']).apply(lambda x: x.strftime('%d/%m/%Y %H:%M') if pd.notnull(x) else "")

                # Liste des colonnes ordonnée
                cols = ['id', 'Nature', 'Parent', 'Ouvert le', 'Terminé le', 'title', 'status', 'priority', 'assigned_to', 'description']
                
                sel = st.dataframe(
                    df_v[cols], 
                    width='stretch', 
                    hide_index=True, 
                    on_select="rerun", 
                    selection_mode="single-row",
                    key=f"grid_{st.session_state.grid_nonce}",
                    column_config={
                        "id": "ID", "Nature": "Nature", "Parent": "Parent",
                        "Ouvert le": "Ouvert le", "Terminé le": "Terminé le",
                        "title": st.column_config.TextColumn("Titre", width="large"),
                        "description": st.column_config.TextColumn("Description", width="medium"),
                        "status": "Statut", "priority": "Priorité", "assigned_to": "Groupe"
                    }
                )

                # 5. Éditeur de Ticket
                if sel and len(sel.selection.rows) > 0:
                    t = f_tasks[list(sel.selection.rows)[0]]; tid = t['id']
                    st.markdown(f"### 🔎 Édition Ticket #{tid}")
                    with st.container(border=True):
                        c1, c2 = st.columns(2)
                        st_list = ["Nouveau", "À faire", "En cours", "Terminé"]
                        c1.text_input("Titre", value=t['title'], key=f"edit_t_{tid}")
                        c1.selectbox("Statut", st_list, index=st_list.index(normalize_status(t['status'])), key=f"edit_s_{tid}")
                        c2.selectbox("Priorité", ["Basse", "Moyenne", "Haute", "Critique"], index=["Basse", "Moyenne", "Haute", "Critique"].index(t['priority']), key=f"edit_p_{tid}")
                        
                        current_grp = next((g for g in st.session_state.support_groups if g['name'] == t['assigned_to']), st.session_state.non_assigne)
                        c2.selectbox("Groupe", options=st.session_state.support_groups, format_func=lambda x: x['name'], key=f"edit_a_{tid}")
                        
                        st.text_area("Description", value=t.get('description', ""), key=f"edit_d_{tid}")
                        
                        b_save, b_del, _ = st.columns([1, 1, 2])
                        b_save.button("💾 SAUVEGARDER", on_click=cb_update_task, args=(tid,), type="secondary", key=f"save_{tid}")
                        if st.session_state.authenticated:
                            b_del.button("🗑️ SUPPRIMER", on_click=cb_delete_task, args=(tid,), type="secondary", key=f"del_{tid}")
            else: st.info("Aucun résultat.")
    except Exception as e: st.error(f"Erreur d'affichage : {e}")

# --- TAB 1 (0): Dashboard (Implemented above) ---

# --- TAB 2 (1): FLOW DESIGNER ---
with tabs[1]:
    if st.session_state.authenticated:
        from flow_components import show_flow_designer
        show_flow_designer(API_URL, WORKFLOWS_FILE, st.session_state["support_groups"])
    else: st.warning("🔐 Accès Admin requis")

# --- TAB 3 (2): BASE DE DONNÉES ---
with tabs[2]:
    if st.session_state.authenticated:
        st.header("🗄️ Base de données")
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
        except: st.error("Impossible de charger les groupes")
    else: st.warning("🔐 Accès Admin requis")

# --- TAB 4 (3): ADMIN TOOLS ---
with tabs[3]:
    if st.session_state.authenticated:
        st.header("🛠️ Maintenance")
        
        c_diag, c_back = st.columns(2)
        
        with c_diag:
            st.subheader("🛡️ Diagnostics")
            if st.button("VÉRIFIER INTÉGRITÉ RÈGLES", type="secondary"):
                try:
                    from engine import check_rules_integrity
                    alerts = check_rules_integrity()
                    if alerts:
                        for a in alerts: st.warning(a)
                    else: st.success("✅ Toutes les règles sont valides.")
                except Exception as e: st.error(f"Erreur : {e}")

        with c_back:
            st.subheader("💾 Backup")
            if st.button("GÉNÉRER BACKUP DB", type="secondary"):
                try:
                    b = requests.get(f"{API_URL}/backup")
                    st.download_button("📥 TÉLÉCHARGER", b.content, "backup.db", type="secondary")
                except: st.error("Erreur Backup")

        st.divider()
        st.subheader("📜 Logs d'Audit")
        try:
            logs = requests.get(f"{API_URL}/audit/logs").json()
            if logs: st.dataframe(pd.DataFrame(logs).sort_values('id', ascending=False), width='stretch', hide_index=True)
        except: st.error("Erreur Logs")
    else: st.warning("🔐 Accès Admin requis")

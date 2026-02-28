# -*- coding: utf-8 -*-
import streamlit as st
import requests
import pandas as pd
import time
import os
from dotenv import load_dotenv
from flow_components import show_flow_designer
from engine import normalize_status

# Load Environment Variables
load_dotenv()

# Configuration
API_URL = os.getenv("API_URL", "http://localhost:8000")
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
    if "create_title" not in st.session_state: st.session_state.create_title = ""
    if "create_desc" not in st.session_state: st.session_state.create_desc = ""
    if "create_priority" not in st.session_state: st.session_state.create_priority = "Moyenne"
    if "new_group_name" not in st.session_state: st.session_state.new_group_name = ""
    if "grid_nonce" not in st.session_state: st.session_state.grid_nonce = 0

# -----------------------------------------------------------------------------
# CALLBACKS
# -----------------------------------------------------------------------------

def cb_create_task():
    if not st.session_state.create_title:
        st.error("Le titre est obligatoire.")
        return
    payload = {
        "title": st.session_state.create_title,
        "description": st.session_state.create_desc,
        "priority": st.session_state.create_priority,
        "assigned_to": st.session_state.get("create_assigned", "Non assigné")
    }
    try:
        response = requests.post(f"{API_URL}/tasks/", json=payload)
        if response.status_code == 200:
            st.session_state.create_title = ""
            st.session_state.create_desc = ""
            st.toast("✅ Tâche créée !")
    except: st.error("Erreur API")

def cb_update_task_dashboard(task_id):
    """Met à jour le ticket sélectionné depuis le dashboard."""
    payload = {
        "title": st.session_state[f"edit_title_{task_id}"],
        "status": st.session_state[f"edit_status_{task_id}"],
        "priority": st.session_state[f"edit_priority_{task_id}"],
        "assigned_to": st.session_state[f"edit_assign_{task_id}"],
        "description": st.session_state[f"edit_desc_{task_id}"],
        "tags": st.session_state[f"edit_tags_{task_id}"]
    }
    try:
        # On utilise la valeur de session pour le paramètre skip_workflow
        skip_val = "true" if st.session_state.get("skip_workflow", False) else "false"
        resp = requests.put(f"{API_URL}/tasks/{task_id}", json=payload, params={"skip_workflow": skip_val})
        if resp.status_code == 200:
            st.toast(f"✅ Ticket #{task_id} mis à jour !")
    except: st.error("Erreur lors de la mise à jour.")

def cb_delete_task(task_id, task_title):
    """Callback pour la suppression avec nettoyage de la sélection."""
    try:
        # Suppression via API
        requests.delete(f"{API_URL}/tasks/{task_id}", timeout=3)
        
        # KEY ROTATION : On change la clé pour forcer le re-render propre
        st.session_state.grid_nonce += 1
            
        # Nettoyage des clés d'édition (Clean State)
        keys_to_del = [k for k in st.session_state.keys() if k.startswith(f"edit_")]
        for k in keys_to_del:
            del st.session_state[k]
        
        st.session_state.delete_confirm_check = False
        st.toast(f"🗑️ Ticket #{task_id} supprimé !")
        
        # On attend une fraction de seconde pour laisser la DB respirer (Cascade enfants)
        time.sleep(0.3)
    except Exception as e:
        st.error(f"Erreur technique lors de la suppression : {e}")

def cb_add_group():
    name = st.session_state.new_group_name.strip()
    if name:
        try:
            resp = requests.post(f"{API_URL}/groups/", json={"name": name})
            if resp.status_code == 200:
                st.session_state.new_group_name = "" 
                refresh_groups()
                st.toast(f"✅ Groupe '{name}' ajouté !")
        except: st.error("Erreur API.")

def cb_delete_group(group_id, group_name):
    try:
        if requests.delete(f"{API_URL}/groups/{group_id}").status_code == 200:
            refresh_groups()
            st.toast(f"🗑️ Groupe '{group_name}' supprimé !")
    except: st.error("Erreur suppression.")

# -----------------------------------------------------------------------------
# INTERFACE
# -----------------------------------------------------------------------------

st.set_page_config(page_title="LiteFlow Manager", layout="wide", page_icon="⚡", initial_sidebar_state="expanded")

def inject_custom_css():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        @import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap');

        /* Hide Streamlit Header, Footer, and MainMenu with high specificity */
        #MainMenu {visibility: hidden !important;}
        footer {visibility: hidden !important;}
        header {visibility: hidden !important;}
        
        /* Remove Streamlit default padding and max-width constraints */
        .block-container {
            padding-top: 2rem !important;
            padding-bottom: 0rem !important;
            padding-left: 1rem !important;
            padding-right: 1rem !important;
            max-width: 100% !important; /* Allow the layout to span wide */
        }

        /* Ensure the body takes full height and uses Inter font */
        html, body, [class*="css"], [class*="st-"] {
            font-family: 'Inter', sans-serif !important;
        }

        /* Adjust for fixed headers if necessary in Streamlit context */
        .stApp {
            margin-top: -56px !important;
            background-color: #f6f6f8; /* background-light */
        }

        /* --- STITCH METRICS PILLS --- */
        .status-pill-resolved { background-color: #f0fdf4; color: #166534; }
        .status-pill-pending { background-color: #fffbeb; color: #92400e; }
        .status-pill-total { background-color: #eef2ff; color: #3730a3; }
        
        .card-shadow {
            box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.05), 0 1px 2px 0 rgba(0, 0, 0, 0.03);
            transition: all 0.2s ease-in-out;
        }
        .card-shadow:hover {
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.05), 0 4px 6px -2px rgba(0, 0, 0, 0.02);
            transform: translateY(-2px);
        }

        /* Sidebar Styling */
        [data-testid="stSidebar"] {
            background-color: #ffffff;
            border-right: 1px solid #e2e8f0;
        }
        
        /* Containers */
        [data-testid="stVerticalBlockBorderWrapper"] {
            border-radius: 16px; /* 2xl matches stitch */
            background-color: #ffffff;
            border: 1px solid #f1f5f9 !important;
        }

        /* Buttons */
        [data-testid="baseButton-primary"] {
            background-color: #5048e5;
            border: none;
            border-radius: 0.75rem; /* rounded-xl */
            font-weight: 600;
            color: #ffffff !important;
            box-shadow: 0 4px 6px -1px rgba(80, 72, 229, 0.2), 0 2px 4px -2px rgba(80, 72, 229, 0.2);
        }
        [data-testid="baseButton-primary"]:hover {
            opacity: 0.9;
        }

        [data-testid="baseButton-secondary"] {
            border-radius: 0.75rem; /* rounded-xl */
            border: 1px solid #e2e8f0;
            background-color: #ffffff;
            color: #475569;
            font-weight: 600;
        }
        [data-testid="baseButton-secondary"]:hover {
            background-color: #f8fafc;
        }

        /* Inputs */
        div[data-baseweb="input"] input, div[data-baseweb="select"] {
            border-radius: 0.75rem !important; /* rounded-xl */
            background-color: #f1f5f9;
            border: none;
        }
        div[data-baseweb="input"]:focus-within, div[data-baseweb="select"]:focus-within {
             outline: 2px solid rgba(80, 72, 229, 0.2); 
        }

        /* Titles and Tabs */
        h1, h2, h3 {
            font-weight: 700 !important;
            letter-spacing: -0.025em; /* tracking-tight */
            color: #0f172a; /* text-slate-900 */
        }
        [data-testid="stTabs"] button {
            font-weight: 600;
            font-size: 1rem;
            color: #64748b;
        }
        [data-testid="stTabs"] button[aria-selected="true"] {
            color: #5048e5;
        }
    </style>
    """, unsafe_allow_html=True)

inject_custom_css()
init_state()

# SIDEBAR
st.sidebar.markdown(
    """
    <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 20px;">
        <div style="background-color: #5048e5; padding: 6px; border-radius: 8px; display: flex; align-items: center; justify-content: center;">
            <span class="material-symbols-outlined" style="color: white; font-size: 20px;">bolt</span>
        </div>
        <h1 style="margin: 0; font-size: 20px; font-weight: 700; letter-spacing: -0.025em; color: #0f172a;">LiteFlow <span style="color: #5048e5; font-weight: 500;">Pro</span></h1>
    </div>
    """, unsafe_allow_html=True
)

if not st.session_state.authenticated:
    pwd = st.sidebar.text_input("Code Admin", type="password")
    if st.sidebar.button("Déverrouiller", width='stretch'):
        if pwd == ADMIN_PASSWORD:
            st.session_state.authenticated = True
            st.rerun()
else:
    st.sidebar.success("✅ Administration déverrouillée")
    if st.sidebar.button("Se déconnecter", width='stretch'):
        st.session_state.authenticated = False
        st.rerun()

st.sidebar.divider()
st.sidebar.markdown("<p style='font-size: 11px; font-weight: 700; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 8px;'>Création Express</p>", unsafe_allow_html=True)
with st.sidebar.container(border=True):
    st.text_input("Titre du ticket", key="create_title", placeholder="Brève description...")
    st.selectbox("Niveau de Priorité", ["Basse", "Moyenne", "Haute", "Critique"], key="create_priority", index=1)
    st.selectbox("Assignation Automatique", st.session_state["support_groups"], key="create_assigned")
    st.button("➕ Créer le ticket", on_click=cb_create_task, width='stretch', type="primary")

st.markdown(
    """
    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 24px;">
        <h1 style='color: #0f172a; margin: 0;'>Dashboard Opérationnel</h1>
    </div>
    """, 
    unsafe_allow_html=True
)

tabs = st.tabs(["📋 Liste des tâches", "⚡ Flow Designer", "📊 Base de données", "🛠️ Admin Tools"])

# --- TAB 1: DASHBOARD ---
with tabs[0]:
    c1, c2 = st.columns([1, 4])
    with c1: st.button("🔄 Actualiser", width='stretch')
    with c2: search = st.text_input("Recherche rapide", placeholder="Rechercher par mot-clé, ID, ou assigné...", label_visibility="collapsed")

    try:
        resp = requests.get(f"{API_URL}/tasks/?limit=1000")
        if resp.status_code == 200:
            all_data = resp.json()
            if all_data:
                # Calcul des statistiques pour les Metrics (Stitch Layout)
                total_tickets = len(all_data)
                resolved = len([t for t in all_data if normalize_status(t['status']) == "Terminé"])
                pending = total_tickets - resolved
                
                # HTML Metrics Dashboard using Stitch Design
                st.markdown(f"""
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 1rem; margin-bottom: 1.5rem;">
                    <!-- Total Metrics -->
                    <div class="card-shadow" style="background: white; padding: 1.5rem; border-radius: 1rem; border: 1px solid #f1f5f9; display: flex; justify-content: space-between; align-items: flex-start;">
                        <div>
                            <p style="font-size: 11px; font-weight: 700; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.1em; margin: 0;">Total Tickets</p>
                            <h3 style="font-size: 2.25rem; font-weight: 800; color: #0f172a; margin: 0.5rem 0 0 0;">{total_tickets}</h3>
                            <div style="display: flex; align-items: center; gap: 6px; margin-top: 12px; color: #059669; font-size: 14px; font-weight: 600;">
                                <span class="material-symbols-outlined" style="font-size: 18px;">trending_up</span>
                                <span>Volume Global</span>
                            </div>
                        </div>
                        <div class="status-pill-total" style="width: 48px; height: 48px; border-radius: 12px; display: flex; align-items: center; justify-content: center;">
                            <span class="material-symbols-outlined">confirmation_number</span>
                        </div>
                    </div>
                    <!-- Resolved -->
                    <div class="card-shadow" style="background: white; padding: 1.5rem; border-radius: 1rem; border: 1px solid #f1f5f9; display: flex; justify-content: space-between; align-items: flex-start;">
                        <div>
                            <p style="font-size: 11px; font-weight: 700; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.1em; margin: 0;">Résolus</p>
                            <h3 style="font-size: 2.25rem; font-weight: 800; color: #0f172a; margin: 0.5rem 0 0 0;">{resolved}</h3>
                            <div style="display: flex; align-items: center; gap: 6px; margin-top: 12px; color: #059669; font-size: 14px; font-weight: 600;">
                                <span class="material-symbols-outlined" style="font-size: 18px;">check_circle</span>
                                <span>Terminés</span>
                            </div>
                        </div>
                        <div class="status-pill-resolved" style="width: 48px; height: 48px; border-radius: 12px; display: flex; align-items: center; justify-content: center;">
                            <span class="material-symbols-outlined">verified</span>
                        </div>
                    </div>
                    <!-- Pending -->
                    <div class="card-shadow" style="background: white; padding: 1.5rem; border-radius: 1rem; border: 1px solid #f1f5f9; display: flex; justify-content: space-between; align-items: flex-start;">
                        <div>
                            <p style="font-size: 11px; font-weight: 700; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.1em; margin: 0;">En Attente</p>
                            <h3 style="font-size: 2.25rem; font-weight: 800; color: #0f172a; margin: 0.5rem 0 0 0;">{pending}</h3>
                            <div style="display: flex; align-items: center; gap: 6px; margin-top: 12px; color: #d97706; font-size: 14px; font-weight: 600;">
                                <span class="material-symbols-outlined" style="font-size: 18px;">schedule</span>
                                <span>En Cours</span>
                            </div>
                        </div>
                        <div class="status-pill-pending" style="width: 48px; height: 48px; border-radius: 12px; display: flex; align-items: center; justify-content: center;">
                            <span class="material-symbols-outlined">hourglass_empty</span>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                df = pd.DataFrame(all_data)
                status_map = {"Nouveau": "🔵 Nouveau", "À faire": "🟡 À faire", "En cours": "🟢 En cours", "Terminé": "⚪ Terminé"}
                priority_map = {"Critique": "🚨 Critique", "Haute": "🔴 Haute", "Moyenne": "🟠 Moyenne", "Basse": "🟢 Basse"}
                
                df['status_view'] = df['status'].apply(lambda x: status_map.get(normalize_status(x), x))
                df['priority_view'] = df['priority'].apply(lambda x: priority_map.get(x, x))
                
                if search:
                    df = df[df.apply(lambda row: search.lower() in row.astype(str).str.lower().values, axis=1)]

                # GRILLE DE DONNÉES
                # Key Rotation Pattern
                grid_key = f"main_grid_{st.session_state.grid_nonce}"

                selection = st.dataframe(
                    df[['id', 'title', 'status_view', 'priority_view', 'assigned_to', 'parent_id']],
                    width='stretch', 
                    hide_index=True, 
                    on_select="rerun", 
                    selection_mode="single-row", 
                    key=grid_key
                )

                # ÉDITEUR DE TICKET (Apparaît lors de la sélection)
                if selection and len(selection.selection.rows) > 0:
                    selected_idx = list(selection.selection.rows)[0]
                    
                    # BLINDAGE : Si l'index est hors limites (suppression concurrente), on reload
                    if selected_idx >= len(all_data):
                        st.rerun()
                    
                    t = all_data[selected_idx]
                    tid = t['id']

                    st.markdown(f"""
                        <div style="margin-top: 1rem; margin-bottom: 0.5rem; display: flex; align-items: center; gap: 8px;">
                            <span style="background: #f1f5f9; padding: 4px 10px; border-radius: 6px; font-weight: 700; color: #475569; font-size: 14px;">#{tid}</span>
                            <h3 style="margin: 0; padding: 0;">Gestion du Ticket</h3>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    with st.container(border=True):
                        col_a, col_b = st.columns(2)
                        
                        with col_a:
                            st.text_input("Titre du ticket", value=t['title'], key=f"edit_title_{tid}")
                        
                        # Statut avec normalisation pour l'index
                        curr_st = normalize_status(t['status'])
                        st_opts = ["Nouveau", "À faire", "En cours", "Terminé"]
                        st.selectbox("Statut (Cycle de vie)", st_opts, index=st_opts.index(curr_st) if curr_st in st_opts else 0, key=f"edit_status_{tid}")
                        
                        st.selectbox("Niveau d'urgence", ["Basse", "Moyenne", "Haute", "Critique"], index=["Basse", "Moyenne", "Haute", "Critique"].index(t['priority']), key=f"edit_priority_{tid}")

                        with col_b:
                            st.selectbox("Groupe assigné", st.session_state["support_groups"], index=st.session_state["support_groups"].index(t['assigned_to']) if t['assigned_to'] in st.session_state["support_groups"] else 0, key=f"edit_assign_{tid}")
                            st.text_input("Tags / Étiquettes", value=t['tags'] or "", key=f"edit_tags_{tid}")
                            st.text_area("Description / Historique", value=t['description'] or "", key=f"edit_desc_{tid}", height=115)

                    # BOUTONS D'ACTION
                    act_col1, act_col2, act_col3 = st.columns([1, 1, 2])
                    
                    act_col1.button("💾 Enregistrer les modifications", type="primary", on_click=cb_update_task_dashboard, args=(tid,), width='stretch')
                    
                    # Bouton Supprimer réservé à l'ADMIN
                    if st.session_state.authenticated:
                        if act_col2.button("🗑️ Supprimer l'enregistrement", type="secondary", width='stretch'):
                            cb_delete_task(tid, t['title'])
                            st.rerun()
                    else:
                        act_col2.info("🔓 Login Admin pour supprimer")
            else:
                st.info("Aucun ticket en cours.")
    except: st.error("Lien avec l'API perdu.")

# --- FLOW DESIGNER ---
with tabs[1]:
    if st.session_state.authenticated:
        show_flow_designer(API_URL, WORKFLOWS_FILE, st.session_state["support_groups"])
    else: st.warning("🔒 Authentification requise.")

# --- BASE DE DONNÉES ---
with tabs[2]:
    if st.session_state.authenticated:
        st.header("📊 Master Data : Groupes")
        with st.container(border=True):
            c_in, c_bt = st.columns([3, 1])
            c_in.text_input("Nom du nouveau groupe", key="new_group_name")
            c_bt.button("Ajouter", on_click=cb_add_group, width='stretch', type="primary")
        
        try:
            r_gr = requests.get(f"{API_URL}/groups/")
            if r_gr.status_code == 200:
                gr_data = r_gr.json()
                if gr_data:
                    st.dataframe(pd.DataFrame(gr_data), width='stretch', hide_index=True)
                    st.divider()
                    g_del = st.selectbox("Sélectionner un groupe à retirer", options=gr_data, format_func=lambda x: x['name'])
                    st.button("🗑️ Supprimer le groupe", on_click=cb_delete_group, args=(g_del['id'], g_del['name']), type="primary")
        except: st.error("Erreur base.")

# --- ADMINISTRATION ---
with tabs[3]:
    st.info("Espace de maintenance système.")
    if st.session_state.authenticated:
        st.write("L'administration complète est active.")
        st.checkbox("Désactiver le workflow lors des updates", key="skip_workflow")
    else:
        st.warning("Veuillez vous connecter via la barre latérale.")
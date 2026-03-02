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
    
    # Form States
    if "create_title" not in st.session_state: st.session_state.create_title = ""
    if "create_desc" not in st.session_state: st.session_state.create_desc = ""
    if "create_priority" not in st.session_state: st.session_state.create_priority = "Moyenne"
    if "create_assigned" not in st.session_state: st.session_state.create_assigned = "Non assigné"
    if "new_group_name" not in st.session_state: st.session_state.new_group_name = ""

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
        "assigned_to": st.session_state.create_assigned
    }
    try:
        if requests.post(f"{API_URL}/tasks/", json=payload).status_code == 200:
            st.session_state.create_title = ""
            st.session_state.create_desc = ""
            st.toast("✅ Ticket créé")
    except: st.error("API Error")

def cb_update_task_dashboard(task_id):
    payload = {
        "title": st.session_state[f"edit_title_{task_id}"],
        "status": st.session_state[f"edit_status_{task_id}"],
        "priority": st.session_state[f"edit_priority_{task_id}"],
        "assigned_to": st.session_state[f"edit_assign_{task_id}"],
        "description": st.session_state[f"edit_desc_{task_id}"],
        "tags": st.session_state.get(f"edit_tags_{task_id}", "")
    }
    try:
        if requests.put(f"{API_URL}/tasks/{task_id}", json=payload).status_code == 200:
            st.toast(f"✅ Mise à jour effectuée")
    except: st.error("Erreur Update")

def cb_delete_task(task_id):
    try:
        if requests.delete(f"{API_URL}/tasks/{task_id}").status_code == 200:
            st.session_state.grid_nonce += 1
            st.session_state.delete_confirm_check = False
            st.toast("🗑️ Supprimé")
    except: st.error("Erreur Delete")

# -----------------------------------------------------------------------------
# STYLE & DESIGN (FIX RÉGRESSION)
# -----------------------------------------------------------------------------

st.set_page_config(page_title="LiteFlow Pro", layout="wide", page_icon="⚡")
init_state()

st.markdown("""
<style>
    /* 1. Fond Global Cloud */
    .stApp { background-color: #f1f5f9; }

    /* 2. Sidebar Navy sans blocs blancs */
    section[data-testid="stSidebar"] { 
        background-color: #0f172a !important; 
    }
    section[data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"] {
        background-color: transparent !important;
        border: none !important;
        box-shadow: none !important;
    }
    section[data-testid="stSidebar"] h1, 
    section[data-testid="stSidebar"] h3, 
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] .stMarkdown p { 
        color: #ffffff !important; 
    }

    /* 3. Boutons - BLEU ACTION SAAS */
    .stButton > button {
        background-color: #2563eb !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 700 !important;
        width: 100% !important;
    }
    .stButton > button:hover {
        background-color: #1d4ed8 !important;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3) !important;
    }

    /* 4. En-têtes page principale */
    h1, h2, h3, h4 { color: #0f172a !important; font-weight: 700 !important; }

    /* 5. Cartes KPI (Texte blanc sur Navy) */
    .kpi-card {
        background-color: #0f172a;
        border-radius: 12px;
        padding: 20px;
        color: #ffffff;
        box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1);
        border: 1px solid #1e293b;
    }
    .kpi-label { font-size: 0.8rem; color: #94a3b8; text-transform: uppercase; }
    .kpi-value { font-size: 2.2rem; font-weight: 800; color: #ffffff; margin: 5px 0; }

    /* 6. Conteneurs Main Content - Blanc Pur */
    [data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #ffffff !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 12px !important;
    }
</style>
""", unsafe_allow_html=True)

# --- SIDEBAR (Navy Profond) ---
with st.sidebar:
    st.markdown("# ⚡ LiteFlow Pro")
    
    if not st.session_state.authenticated:
        pwd = st.text_input("Accès Admin", type="password")
        if st.button("DÉVERROUILLER"):
            if pwd == ADMIN_PASSWORD:
                st.session_state.authenticated = True
                st.rerun()
    else:
        st.success("Administrateur")
        if st.button("QUITTER LA SESSION"):
            st.session_state.authenticated = False
            st.rerun()

    st.divider()
    st.markdown("### 🚀 CRÉATION EXPRESS")
    # Pas de container blanc ici pour respecter le Navy
    st.text_input("Titre du ticket", key="create_title", placeholder="Sujet...")
    st.text_area("Description...", key="create_desc", height=70)
    st.selectbox("Priorité", ["Basse", "Moyenne", "Haute", "Critique"], key="create_priority")
    st.selectbox("Assignation", st.session_state["support_groups"], key="create_assigned")
    st.button("➕ OUVRIR LE TICKET", on_click=cb_create_task)

# --- MAIN ---
st.title("📑 Dashboard Opérationnel")

tabs = st.tabs(["📋 Liste des tâches", "⚡ Flow Designer", "🗄️ Base de données", "🛠️ Admin Tools"])

# --- TAB 1: DASHBOARD ---
with tabs[0]:
    try:
        resp = requests.get(f"{API_URL}/tasks/?limit=1000")
        if resp.status_code == 200:
            all_data = resp.json()
            df = pd.DataFrame(all_data) if all_data else pd.DataFrame()
            
            # KPI Cards
            k1, k2, k3 = st.columns(3)
            with k1: st.markdown(f'<div class="kpi-card"><div class="kpi-label">📊 Tickets Totaux</div><div class="kpi-value">{len(df)}</div></div>', unsafe_allow_html=True)
            with k2: 
                res = len(df[df['status'] == 'Terminé']) if not df.empty else 0
                st.markdown(f'<div class="kpi-card"><div class="kpi-label">✅ Clôturés</div><div class="kpi-value">{res}</div></div>', unsafe_allow_html=True)
            with k3:
                act = len(df[df['status'] != 'Terminé']) if not df.empty else 0
                st.markdown(f'<div class="kpi-card"><div class="kpi-label">⏳ En Attente</div><div class="kpi-value">{act}</div></div>', unsafe_allow_html=True)

            st.write("") # Spacer
            
            search = st.text_input("Recherche rapide", placeholder="Filtrer...", label_visibility="collapsed")
            if not df.empty:
                status_map = {"Nouveau": "🔵 Nouveau", "À faire": "🟡 À faire", "En cours": "🟢 En cours", "Terminé": "⚪ Terminé"}
                priority_map = {"Critique": "🔥 Critique", "Haute": "🔴 Haute", "Moyenne": "🟠 Moyenne", "Basse": "🔵 Basse"}
                df['status_view'] = df['status'].apply(lambda x: status_map.get(normalize_status(x), x))
                df['priority_view'] = df['priority'].apply(lambda x: priority_map.get(x, x))
                
                if search:
                    df = df[df.apply(lambda r: search.lower() in r.astype(str).str.lower().values, axis=1)]

                sel = st.dataframe(
                    df[['id', 'title', 'status_view', 'priority_view', 'assigned_to', 'parent_id']],
                    width='stretch', hide_index=True, on_select="rerun", selection_mode="single-row", 
                    key=f"grid_nonce_{st.session_state.grid_nonce}"
                )

                if sel and len(sel.selection.rows) > 0:
                    t = df.iloc[list(sel.selection.rows)[0]]
                    tid = t['id']
                    st.markdown(f"### 🔎 Édition Ticket #{tid}")
                    with st.container(border=True):
                        ca, cb = st.columns(2)
                        with ca:
                            st.text_input("Titre", value=t['title'], key=f"edit_title_{tid}")
                            curr_st = normalize_status(t['status']); st_opts = ["Nouveau", "À faire", "En cours", "Terminé"]
                            st.selectbox("Statut", st_opts, index=st_opts.index(curr_st) if curr_st in st_opts else 0, key=f"edit_status_{tid}")
                        with cb:
                            st.selectbox("Urgence", ["Basse", "Moyenne", "Haute", "Critique"], index=["Basse", "Moyenne", "Haute", "Critique"].index(t['priority']), key=f"edit_priority_{tid}")
                            st.selectbox("Assigné", st.session_state["support_groups"], index=st.session_state["support_groups"].index(t['assigned_to']) if t['assigned_to'] in st.session_state["support_groups"] else 0, key=f"edit_assign_{tid}")
                        
                        st.text_area("Description", value=t.get('description', ""), key=f"edit_desc_{tid}")
                        
                        btn1, btn2, _ = st.columns([1, 1, 2])
                        btn1.button("💾 ENREGISTRER", type="primary", on_click=cb_update_task_dashboard, args=(tid,), width='stretch')
                        if st.session_state.authenticated:
                            btn2.button("🗑️ SUPPRIMER", on_click=cb_delete_task, args=(tid,), width='stretch')
            else: st.info("Aucun ticket.")
    except: st.error("Erreur API.")

# --- AUTRES TABS (SÉCURISÉS) ---
with tabs[1]:
    if st.session_state.authenticated: show_flow_designer(API_URL, WORKFLOWS_FILE, st.session_state["support_groups"])
    else: st.warning("🔐 Accès Admin requis.")

with tabs[2]:
    if st.session_state.authenticated:
        st.header("🗄️ Base de données")
        r_g = requests.get(f"{API_URL}/groups/")
        if r_g.status_code == 200: st.dataframe(pd.DataFrame(r_g.json()), width='stretch', hide_index=True)
    else: st.warning("🔐 Accès Admin requis.")

# --- TAB 4: ADMIN TOOLS ---
with tabs[3]:
    if not st.session_state.authenticated:
        st.warning("🔐 Accès Admin requis.")
    else:
        st.header("🛠️ Administration & Maintenance")

        # ── Section 1 : Logs d'Audit ──────────────────────────────────────
        st.subheader("📋 Logs d'Audit")
        with st.container(border=True):
            try:
                r_logs = requests.get(f"{API_URL}/audit/logs", timeout=5)
                if r_logs.status_code == 200:
                    logs_data = r_logs.json()
                    if logs_data:
                        df_logs = pd.DataFrame(logs_data[:100])
                        # Format timestamp column if present
                        if 'timestamp' in df_logs.columns:
                            df_logs['timestamp'] = pd.to_datetime(df_logs['timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')
                        # Reorder columns for readability
                        cols_order = [c for c in ['id', 'timestamp', 'task_id', 'message'] if c in df_logs.columns]
                        st.dataframe(df_logs[cols_order], use_container_width=True, hide_index=True)
                        st.caption(f"📊 {len(logs_data)} entrée(s) au total — affichage des 100 dernières.")
                    else:
                        st.info("Aucun log d'audit enregistré.")
                else:
                    st.error(f"Erreur API : HTTP {r_logs.status_code}")
            except Exception as e:
                st.error(f"Impossible de contacter l'API : {e}")

        st.write("")  # Spacer

        # ── Section 2 : Sauvegarde de la base de données ─────────────────
        st.subheader("💾 Sauvegarde")
        with st.container(border=True):
            st.markdown("Génère une copie horodatée du fichier `workflow.db` et propose son téléchargement.")
            if st.button("⬇️ Générer une sauvegarde"):
                try:
                    r_backup = requests.get(f"{API_URL}/backup", timeout=15)
                    if r_backup.status_code == 200:
                        # Determine filename from Content-Disposition header or default
                        cd = r_backup.headers.get("content-disposition", "")
                        fname = "workflow_backup.db"
                        if "filename=" in cd:
                            fname = cd.split("filename=")[-1].strip().strip('"')
                        st.download_button(
                            label=f"📥 Télécharger {fname}",
                            data=r_backup.content,
                            file_name=fname,
                            mime="application/octet-stream"
                        )
                        st.success(f"✅ Sauvegarde prête : `{fname}`")
                    else:
                        st.error(f"Erreur lors de la sauvegarde : HTTP {r_backup.status_code}")
                except Exception as e:
                    st.error(f"Impossible de contacter l'API : {e}")

        st.write("")  # Spacer

        # ── Section 3 : Vérification de l'intégrité des règles ───────────
        st.subheader("🔍 Intégrité des règles Workflow")
        with st.container(border=True):
            st.markdown("Analyse le fichier `workflows.yaml` et signale les règles mal configurées.")
            if st.button("🛡️ Vérifier l'intégrité"):
                try:
                    from engine import check_rules_integrity
                    alerts = check_rules_integrity()
                    if alerts:
                        st.warning(f"⚠️ {len(alerts)} problème(s) détecté(s) :")
                        for alert in alerts:
                            st.error(alert)
                    else:
                        st.success("✅ Toutes les règles sont valides et bien configurées.")
                except Exception as e:
                    st.error(f"Erreur lors de la vérification : {e}")
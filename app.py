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

@st.cache_data(ttl=60)
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
    
    # Données de fondation (Smart loading)
    if "classifications" not in st.session_state: st.session_state["classifications"] = fetch_data("classifications")
    if "support_groups" not in st.session_state: st.session_state["support_groups"] = fetch_data("groups")
    if "locations" not in st.session_state: st.session_state["locations"] = fetch_data("locations")
    if "non_assigne" not in st.session_state: st.session_state["non_assigne"] = {"id": None, "name": "Non assigné"}

    # Formulaires
    for f in ["create_title", "create_desc", "new_group_name", "new_nature_name", 
              "new_user_fname", "new_user_lname", "new_user_addr",
              "new_loc_name", "new_loc_addr", "new_loc_zip", "new_loc_city"]:
        if f not in st.session_state: st.session_state[f] = ""
    if "new_user_groups" not in st.session_state: st.session_state.new_user_groups = []
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
            st.toast("✅ Ticket enregistré")
            # Reset des champs
            st.session_state.create_title = ""
            st.session_state.create_desc = ""
            st.session_state.create_priority = "Moyenne"
            st.session_state.create_assigned = st.session_state["non_assigne"]
            st.cache_data.clear()
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
            st.cache_data.clear()
    except: st.error("Erreur")

def cb_delete_task(tid):
    try:
        if requests.delete(f"{API_URL}/tasks/{tid}").status_code == 200:
            st.session_state.grid_nonce += 1
            st.toast("🗑️ Ticket supprimé")
            st.cache_data.clear()
    except: st.error("Erreur")

def cb_group_action(action, name=None, gid=None, classification_ids=None):
    try:
        if action == "add":
            payload = {"name": name, "classification_ids": classification_ids}
            if requests.post(f"{API_URL}/groups/", json=payload).status_code == 200:
                st.toast(f"✅ Groupe {name} ajouté")
                # Reset des champs de création
                st.session_state.new_group_name = ""
                st.session_state.new_group_nats = []
                st.cache_data.clear()
        elif action == "update":
            payload = {"name": name, "classification_ids": classification_ids}
            if requests.put(f"{API_URL}/groups/{gid}", json=payload).status_code == 200:
                st.toast(f"✅ Groupe {name} mis à jour")
                st.cache_data.clear()
        elif action == "del":
            if requests.delete(f"{API_URL}/groups/{gid}").status_code == 200:
                st.toast("🗑️ Groupe supprimé")
                st.cache_data.clear()
    except: st.error("Erreur API")

def cb_nature_action(action, name=None, nid=None):
    try:
        if action == "add":
            payload = {"name": name}
            if requests.post(f"{API_URL}/classifications/", json=payload).status_code == 200:
                st.toast(f"✅ Nature '{name}' ajoutée")
                st.session_state.new_nature_name = ""
                st.cache_data.clear()
        elif action == "del":
            resp = requests.delete(f"{API_URL}/classifications/{nid}")
            if resp.status_code == 200:
                st.toast("🗑️ Nature supprimée")
                st.cache_data.clear()
            else:
                try:
                    detail = resp.json().get('detail', "Erreur")
                except: detail = "Erreur"
                st.error(f"❌ {detail}")
    except: st.error("Erreur API")

def cb_update_nature(nid, old_name, new_name):
    if not new_name.strip():
        st.warning("⚠️ Le nom ne peut pas être vide."); return
    if new_name.strip() == old_name:
        st.warning("⚠️ Le nouveau nom est identique à l'ancien."); return
        
    try:
        payload = {"name": new_name}
        resp = requests.put(f"{API_URL}/classifications/{nid}", json=payload)
        if resp.status_code == 200:
            # Audit log
            requests.post(f"{API_URL}/audit/logs", json={"message": f"[ADMIN] Nature renommée : {old_name} -> {new_name}"})
            st.session_state.classifications = fetch_data("classifications")
            # Force la mise à jour immédiate pour le selectbox
            st.session_state[f"edit_classif_name_{nid}"] = ""
            st.toast("✅ Nature mise à jour")
            st.cache_data.clear()
        else:
            try:
                detail = resp.json().get('detail', "Erreur")
            except: detail = "Erreur"
            st.error(f"❌ {detail}")
    except: st.error("Erreur API")

def cb_user_action(action, uid=None, data=None):
    try:
        if action == "add":
            resp = requests.post(f"{API_URL}/users/", json=data)
            if resp.status_code == 200:
                user = resp.json()
                st.toast(f"✅ Utilisateur {user['user_code']} ajouté")
                st.info(f"✨ Utilisateur créé avec succès. Code : {user['user_code']}")
                requests.post(f"{API_URL}/audit/logs", json={"message": f"[ADMIN] Utilisateur créé : {user['user_code']} ({user['first_name']} {user['last_name']})"})
                # Reset complet
                st.session_state.new_user_fname = ""
                st.session_state.new_user_lname = ""
                st.session_state.new_user_addr = ""
                st.session_state.new_user_groups = []
                st.cache_data.clear()
        elif action == "update":
            resp = requests.put(f"{API_URL}/users/{uid}", json=data)
            if resp.status_code == 200:
                st.toast("✅ Utilisateur mis à jour")
                requests.post(f"{API_URL}/audit/logs", json={"message": f"[ADMIN] Utilisateur ID {uid} modifié"})
                st.cache_data.clear()
        elif action == "del":
            resp = requests.delete(f"{API_URL}/users/{uid}")
            if resp.status_code == 200:
                st.toast("🗑️ Utilisateur supprimé")
                requests.post(f"{API_URL}/audit/logs", json={"message": f"[ADMIN] Utilisateur ID {uid} supprimé"})
                st.cache_data.clear()
    except Exception as e: st.error(f"Erreur User Action: {e}")

def cb_location_action(action, loc_id=None, data=None):
    try:
        if action == "add":
            resp = requests.post(f"{API_URL}/locations/", json=data)
            if resp.status_code == 200:
                loc = resp.json()
                st.toast(f"✅ Localisation '{loc['name']}' ajoutée")
                requests.post(f"{API_URL}/audit/logs", json={"message": f"[ADMIN] Localisation créée : {loc['name']} ({loc['city']})"})
                # Reset
                st.session_state.new_loc_name = ""
                st.session_state.new_loc_addr = ""
                st.session_state.new_loc_zip = ""
                st.session_state.new_loc_city = ""
                st.cache_data.clear() # Invalide le cache pour rafraîchir la liste
        elif action == "del":
            resp = requests.delete(f"{API_URL}/locations/{loc_id}")
            if resp.status_code == 200:
                st.toast("🗑️ Localisation supprimée")
                requests.post(f"{API_URL}/audit/logs", json={"message": f"[ADMIN] Localisation ID {loc_id} supprimée"})
                st.cache_data.clear()
    except Exception as e: st.error(f"Erreur Location Action: {e}")

def cb_update_location(loc_id, old_name, data):
    try:
        resp = requests.put(f"{API_URL}/locations/{loc_id}", json=data)
        if resp.status_code == 200:
            new_loc = resp.json()
            st.toast("✅ Localisation mise à jour")
            requests.post(f"{API_URL}/audit/logs", json={"message": f"[ADMIN] Localisation ID {loc_id} modifiée ({old_name} -> {new_loc['name']})"})
            st.cache_data.clear()
    except Exception as e: st.error(f"Erreur Update Location: {e}")

def cb_on_edit_nature_change(tid):
    """Gère la requalification dynamique des tickets dans l'éditeur."""
    new_nature = st.session_state.get(f"edit_c_{tid}")
    current_assigned = st.session_state.get(f"edit_a_{tid}")
    
    if new_nature and current_assigned and current_assigned.get('id'):
        # Vérifie si le groupe actuel possède la compétence pour la nouvelle nature
        is_competent = any(c['id'] == new_nature['id'] for c in current_assigned.get('classifications', []))
        if not is_competent:
            st.session_state[f"edit_a_{tid}"] = st.session_state["non_assigne"]
            st.toast("⚠️ Groupe réinitialisé (compétence différente)")

def cb_nature_changed():
    """Vérifie si le groupe assigné supporte toujours la nouvelle nature."""
    nature = st.session_state.get("create_classif")
    assigned = st.session_state.get("create_assigned")
    
    if nature and assigned and assigned.get('id'): # Si un groupe (pas "Non assigné") est sélectionné
        # Vérification des compétences du groupe
        # On cherche si la nature actuelle est dans les classifications du groupe
        is_competent = any(c['id'] == nature['id'] for c in assigned.get('classifications', []))
        if not is_competent:
            st.session_state.create_assigned = st.session_state["non_assigne"]
            st.toast("ℹ️ Groupe réinitialisé (compétence différente)")

# -----------------------------------------------------------------------------
# DESIGN CSS
# -----------------------------------------------------------------------------

st.set_page_config(page_title="LiteFlow Pro", layout="wide", page_icon="⚡")
init_state()

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;600;700&family=Fira+Sans:wght@300;400;500;600;700&display=swap');
    
    html, body, [class*="css"]  {
        font-family: 'Fira Sans', sans-serif !important;
        color: #1E293B !important;
    }
    
    .stApp { background-color: #F8FAFC !important; }
    
    section[data-testid="stSidebar"] { background-color: #1E293B !important; }
    section[data-testid="stSidebar"] label, .sidebar-header, section[data-testid="stSidebar"] p { color: #F8FAFC !important; font-weight: 500 !important; }
    section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] h2, section[data-testid="stSidebar"] h3 { color: #F8FAFC !important; }

    h1, h2, h3, h4 { color: #1E293B !important; font-family: 'Fira Code', monospace !important; font-weight: 700 !important; }

    /* BOUTONS SECONDAIRES (Bleu SaaS) */
    button[data-testid="stBaseButton-secondary"] {
        background-color: #3B82F6 !important;
        color: white !important;
        border: none !important;
        font-weight: 600 !important;
        border-radius: 6px !important;
        transition: all 0.2s ease-in-out;
        cursor: pointer !important;
    }
    button[data-testid="stBaseButton-secondary"]:hover {
        background-color: #2563EB !important;
    }

    /* BOUTONS PRIMAIRES (CTA) */
    button[data-testid="stBaseButton-primary"] {
        background-color: #F97316 !important;
        color: #F8FAFC !important;
        border: none !important;
        font-weight: 600 !important;
        border-radius: 6px !important;
        transition: all 0.2s ease-in-out;
        cursor: pointer !important;
    }
    button[data-testid="stBaseButton-primary"]:hover {
        background-color: #EA580C !important;
    }

    [data-testid="stVerticalBlockBorderWrapper"] { background-color: #FFFFFF !important; border: 1px solid #E2E8F0 !important; border-radius: 8px !important; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }

    /* BOUTONS ROUGES (SUPPRESSION) */
    div.red-btn button[data-testid="stBaseButton-secondary"] {
        background-color: #dc2626 !important;
        color: white !important;
        border: none !important;
    }
    div.red-btn button[data-testid="stBaseButton-secondary"]:hover {
        background-color: #b91c1c !important;
    }
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
    nature = st.selectbox("Nature", options=classifs, format_func=lambda x: x['name'], key="create_classif", on_change=cb_nature_changed)
    
    # Filtrage contextuel des groupes selon la nature
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
                        
                        # --- NATURE (NOUVEAU) ---
                        all_classifs = st.session_state.get("classifications", [])
                        current_nat = next((c for c in all_classifs if c['id'] == t['classification_id']), all_classifs[0] if all_classifs else None)
                        
                        nature_edit = c1.selectbox(
                            "Nature du ticket", 
                            options=all_classifs, 
                            index=all_classifs.index(current_nat) if current_nat in all_classifs else 0,
                            format_func=lambda x: x['name'], 
                            key=f"edit_c_{tid}",
                            disabled=not st.session_state.authenticated,
                            on_change=cb_on_edit_nature_change,
                            args=(tid,)
                        )
                        
                        c1.selectbox("Statut", st_list, index=st_list.index(normalize_status(t['status'])), key=f"edit_s_{tid}")
                        c2.selectbox("Priorité", ["Basse", "Moyenne", "Haute", "Critique"], index=["Basse", "Moyenne", "Haute", "Critique"].index(t['priority']), key=f"edit_p_{tid}")
                        
                        # --- FILTRAGE DES GROUPES (DYNAMIC) ---
                        # On filtre les groupes basés sur la nature sélectionnée dans l'éditeur (nature_edit)
                        valid_groups = [g for g in st.session_state.support_groups if any(c['id'] == nature_edit['id'] for c in g.get('classifications', []))] if nature_edit else []
                        
                        current_grp_name = t['assigned_to']
                        # Si le state a déjà été modifié (ex: par le callback), on l'utilise
                        state_grp = st.session_state.get(f"edit_a_{tid}")
                        if state_grp:
                            current_grp = state_grp
                        else:
                            current_grp = next((g for g in st.session_state.support_groups if g['name'] == current_grp_name), st.session_state.non_assigne)
                        
                        # On s'assure que current_grp est dans les options (pour éviter les erreurs d'Index)
                        options_grp = [st.session_state.non_assigne] + valid_groups
                        if current_grp not in options_grp:
                            # Si le groupe actuel de la DB n'est pas compatible avec la nature (éventuellement suite à un changement manuel hors UI)
                            current_grp = st.session_state.non_assigne
                        
                        selected_grp = c2.selectbox(
                            "Groupe", 
                            options=options_grp, 
                            index=options_grp.index(current_grp),
                            format_func=lambda x: x['name'], 
                            key=f"edit_a_{tid}"
                        )
                        
                        # --- ALERTE VISUELLE (NOUVEAU) ---
                        if selected_grp['id'] is None:
                            c2.warning("🟠 *Attention : Aucun groupe assigné.*")
                        
                        st.text_area("Description", value=t.get('description', ""), key=f"edit_d_{tid}")
                        
                        b_save, b_del, _ = st.columns([1, 1, 2])
                        b_save.button("💾 SAUVEGARDER", on_click=cb_update_task, args=(tid,), type="secondary", key=f"btn_edit_task_save_{tid}")
                        if st.session_state.authenticated:
                            b_del.button("🗑️ SUPPRIMER", on_click=cb_delete_task, args=(tid,), type="secondary", key=f"btn_del_task_{tid}")
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
        st.header("🗄️ Gestionnaire de Données")
        
        # Smart loading: On utilise les données déjà en session ou on fetch une fois
        if "locations" not in st.session_state: st.session_state["locations"] = fetch_data("locations")
        
        # Accès direct à la session sans re-fetch systématique
        target = st.selectbox("Objet à gérer", ["Groupes de Support", "Natures de Ticket", "Utilisateurs", "Localisations"], key="db_mgmt_select")
        
        if st.button("🔄 FORCER LE RAFRAÎCHISSEMENT", type="secondary", use_container_width=True):
            st.cache_data.clear()
            st.session_state["classifications"] = fetch_data("classifications")
            st.session_state["support_groups"] = fetch_data("groups")
            st.session_state["locations"] = fetch_data("locations")
            st.rerun()
            
        st.divider()

        if target == "Groupes de Support":
            # 1. FORMULAIRE DE CRÉATION
            with st.container(border=True):
                st.subheader("➕ Ajouter un Groupe")
                c_name, c_nat = st.columns([1, 1])
                new_name = c_name.text_input("Nom du groupe", key="new_group_name")
                all_classifs = st.session_state.get("classifications", [])
                new_nats = c_nat.multiselect("Natures (Compétences)", options=all_classifs, format_func=lambda x: x['name'], key="new_group_nats")
                
                can_add = bool(new_name.strip()) and len(new_nats) > 0
                st.button("AJOUTER LE GROUPE", 
                          on_click=cb_group_action, 
                          args=("add", new_name, None, [n['id'] for n in new_nats]),
                          disabled=not can_add, 
                          type="secondary",
                          use_container_width=True)

            st.divider()

            # 2. LISTE ET ÉDITION
            try:
                grs = requests.get(f"{API_URL}/groups/").json()
                if grs:
                    df_g = pd.DataFrame(grs)
                    df_g['Compétences'] = df_g['classifications'].apply(lambda x: ", ".join([c['name'] for c in x]))
                    st.subheader("📋 Liste des Groupes")
                    st.dataframe(df_g[['id', 'name', 'Compétences']], width='stretch', hide_index=True)

                    st.divider()
                    st.subheader("✏️ Édition des Compétences")
                    edit_g = st.selectbox("Sélectionner un groupe à modifier", options=grs, format_func=lambda x: x['name'], key="edit_group_sel")
                    if edit_g:
                        current_nat_ids = [c['id'] for c in edit_g['classifications']]
                        default_nats = [c for c in all_classifs if c['id'] in current_nat_ids]
                        
                        edit_nats = st.multiselect(f"Natures pour {edit_g['name']}", 
                                                 options=all_classifs, 
                                                 default=default_nats, 
                                                 format_func=lambda x: x['name'], 
                                                 key=f"edit_nats_{edit_g['id']}")
                        
                        if not edit_nats:
                            st.error("⚠️ Un groupe doit posséder au moins une compétence.")
                        
                        c_save, c_del, _ = st.columns([1, 1, 2])
                        c_save.button("METTRE À JOUR", 
                                     on_click=cb_group_action, 
                                     args=("update", edit_g['name'], edit_g['id'], [n['id'] for n in edit_nats]),
                                     disabled=len(edit_nats) == 0,
                                     type="secondary", use_container_width=True)
                        
                        st.markdown('<div class="red-btn">', unsafe_allow_html=True)
                        c_del.button("SUPPRIMER LE GROUPE", 
                                     on_click=cb_group_action, 
                                     args=("del", None, edit_g['id']),
                                     type="secondary", use_container_width=True,
                                     key=f"btn_del_group_{edit_g['id']}")
                        st.markdown('</div>', unsafe_allow_html=True)
            except Exception as e: st.error(f"Erreur : {e}")

        elif target == "Natures de Ticket":
            # 1. FORMULAIRE DE CRÉATION
            with st.container(border=True):
                st.subheader("➕ Ajouter une Nature")
                new_n_name = st.text_input("Nom de la nouvelle nature", key="new_nature_name")
                st.button("AJOUTER LA NATURE", 
                          on_click=cb_nature_action, 
                          args=("add", new_n_name),
                          disabled=not new_n_name.strip(), 
                          type="secondary",
                          use_container_width=True)

            st.divider()

            # 2. LISTAGE
            try:
                nats = requests.get(f"{API_URL}/classifications/").json()
                if nats:
                    st.subheader("📋 Liste des Natures")
                    st.dataframe(pd.DataFrame(nats), width='stretch', hide_index=True)

                    st.divider()
                    st.subheader("🗑️ Suppression")
                    del_n = st.selectbox("Nature à supprimer", options=nats, format_func=lambda x: x['name'], key="del_nature_sel")
                    if del_n:
                        st.markdown('<div class="red-btn">', unsafe_allow_html=True)
                        st.button("SUPPRIMER LA NATURE", 
                                  on_click=cb_nature_action, 
                                  args=("del", None, del_n['id']),
                                  type="secondary", use_container_width=True,
                                  key=f"btn_del_classif_{del_n['id']}")
                        st.markdown('</div>', unsafe_allow_html=True)
                
                st.divider()
                st.subheader("✏️ Édition d'une Nature")
                with st.container(border=True):
                    # Utiliser classifications de session_state pour synchromisation instantanée
                    all_ns = st.session_state.get("classifications", nats)
                    edit_n = st.selectbox("Sélectionner une nature à modifier", options=all_ns, format_func=lambda x: x['name'], key="edit_nature_sel")
                    if edit_n:
                        new_name = st.text_input("Nouveau nom", placeholder=edit_n['name'], key=f"edit_classif_name_{edit_n['id']}")
                        st.button("METTRE À JOUR LE NOM", 
                                 on_click=cb_update_nature, 
                                 args=(edit_n['id'], edit_n['name'], new_name),
                                 type="secondary", use_container_width=True,
                                 key=f"btn_save_classif_{edit_n['id']}")
            except Exception as e: st.error(f"Erreur : {e}")

        elif target == "Utilisateurs":
            # 1. FORMULAIRE DE CRÉATION OPTIMISÉ (st.form)
            with st.container(border=True):
                st.subheader("➕ Ajouter un Utilisateur")
                with st.form("form_create_user", clear_on_submit=True):
                    c1, c2 = st.columns(2)
                    fname = c1.text_input("Prénom", key="new_user_fname")
                    lname = c2.text_input("Nom", key="new_user_lname")
                    
                    # Remplacement de l'adresse par la localisation
                    locs_options = [{"id": None, "name": "Non localisé", "city": ""}] + st.session_state.get("locations", [])
                    selected_loc = st.selectbox(
                        "Site de rattachement", 
                        options=locs_options, 
                        format_func=lambda x: f"{x['name']} {f'({x['city']})' if x.get('city') else ''}".strip(),
                        key="new_user_loc"
                    )
                    
                    groups_options = st.session_state.get("support_groups", [])
                    if not groups_options:
                        st.warning("⚠️ Aucun groupe détecté.")
                    
                    grps = st.multiselect("Groupes d'appartenance", 
                                         options=groups_options, 
                                         format_func=lambda x: x['name'], 
                                         key="new_user_groups")
                    
                    submitted = st.form_submit_button("AJOUTER L'UTILISATEUR", type="secondary", use_container_width=True)
                    if submitted:
                        if not fname.strip() or not lname.strip():
                            st.error("⚠️ Prénom et Nom sont obligatoires.")
                        else:
                            payload = {
                                "first_name": fname,
                                "last_name": lname,
                                "location_id": selected_loc['id'] if selected_loc else None,
                                "group_ids": [g['id'] for g in grps]
                            }
                            cb_user_action("add", data=payload)
                            st.rerun()

            st.divider()

            # 2. LISTE ET ÉDITION
            try:
                users = requests.get(f"{API_URL}/users/").json()
                if users:
                    df_u = pd.DataFrame(users)
                    df_u['Groupes'] = df_u['groups'].apply(lambda x: ", ".join([g['name'] for g in x]) if x else "")
                    df_u['Site'] = df_u['location'].apply(lambda x: x['name'] if x else "N/A")
                    
                    st.subheader("📋 Liste des Utilisateurs")
                    st.dataframe(df_u[['user_code', 'first_name', 'last_name', 'Site', 'Groupes']], 
                                 column_config={"user_code": "ID Métier", "Site": "Localisation"},
                                 width='stretch', hide_index=True)

                    st.divider()
                    st.subheader("✏️ Édition d'un Utilisateur")
                    with st.container(border=True):
                        edit_u = st.selectbox("Utilisateur à modifier", options=users, 
                                             format_func=lambda x: f"{x['user_code']} - {x['first_name']} {x['last_name']}", 
                                             key="edit_user_sel")
                        if edit_u:
                            with st.form(f"form_edit_user_{edit_u['id']}"):
                                c1, c2 = st.columns(2)
                                u_fname = c1.text_input("Prénom", value=edit_u['first_name'])
                                u_lname = c2.text_input("Nom", value=edit_u['last_name'])
                                
                                # Localisation pour l'édition
                                locs_options = [{"id": None, "name": "Non localisé", "city": ""}] + st.session_state.get("locations", [])
                                current_loc_id = edit_u.get('location_id')
                                try:
                                    def_loc_idx = next(i for i, l in enumerate(locs_options) if l['id'] == current_loc_id)
                                except: def_loc_idx = 0
                                
                                u_loc = st.selectbox(
                                    "Site de rattachement", 
                                    options=locs_options, 
                                    index=def_loc_idx,
                                    format_func=lambda x: f"{x['name']} {f'({x['city']})' if x.get('city') else ''}".strip()
                                )
                                
                                cur_grp_ids = [g['id'] for g in edit_u['groups']]
                                def_grps = [g for g in st.session_state.support_groups if g['id'] in cur_grp_ids]
                                u_grps = st.multiselect("Groupes", options=st.session_state.support_groups, 
                                                       default=def_grps, format_func=lambda x: x['name'])
                                
                                c_save, c_del, _ = st.columns([1, 1, 2])
                                
                                if c_save.form_submit_button("METTRE À JOUR", type="secondary", use_container_width=True):
                                    cb_user_action("update", edit_u['id'], {
                                        "first_name": u_fname,
                                        "last_name": u_lname,
                                        "location_id": u_loc['id'] if u_loc else None,
                                        "group_ids": [g['id'] for g in u_grps]
                                    })
                                    st.rerun()
                                
                            st.markdown('<div class="red-btn">', unsafe_allow_html=True)
                            if st.button("SUPPRIMER L'UTILISATEUR", type="secondary", use_container_width=True, key=f"btn_del_user_{edit_u['id']}"):
                                cb_user_action("del", edit_u['id'])
                                st.rerun()
                            st.markdown('</div>', unsafe_allow_html=True)
            except Exception as e: st.error(f"Erreur Liste Users: {e}")

        elif target == "Localisations":
            # 1. FORMULAIRE DE CRÉATION ISOLÉ
            with st.container(border=True):
                st.subheader("➕ Ajouter une Localisation")
                with st.form("form_create_location", clear_on_submit=True):
                    c1, c2 = st.columns(2)
                    loc_name = c1.text_input("Nom du bâtiment/site", key="new_loc_name")
                    loc_addr = c2.text_input("Adresse", key="new_loc_addr")
                    c3, c4 = st.columns(2)
                    loc_zip = c3.text_input("Code Postal", key="new_loc_zip")
                    loc_city = c4.text_input("Ville", key="new_loc_city")
                    
                    submitted = st.form_submit_button("AJOUTER LA LOCALISATION", type="secondary", use_container_width=True)
                    
                    if submitted:
                        if not loc_name.strip() or not loc_city.strip():
                            st.error("⚠️ Le nom et la ville sont obligatoires.")
                        else:
                            # Directement passer l'action via le callback manuellement (car on est dans un form)
                            payload = {
                                "name": loc_name,
                                "address": loc_addr,
                                "zip_code": loc_zip,
                                "city": loc_city
                            }
                            cb_location_action("add", data=payload)
                            st.rerun()

            st.divider()

            # 2. LISTE ET ÉDITION
            try:
                locs = st.session_state.get("locations", [])
                if locs:
                    st.subheader("📋 Liste des Sites")
                    df_l = pd.DataFrame(locs)
                    st.dataframe(df_l[['name', 'address', 'zip_code', 'city']], 
                                 column_config={"name": "Nom", "address": "Adresse", "zip_code": "CP", "city": "Ville"},
                                 width='stretch', hide_index=True)

                    st.divider()
                    st.subheader("✏️ Édition d'une Localisation")
                    with st.container(border=True):
                        edit_l = st.selectbox("Site à modifier", options=locs, format_func=lambda x: x['name'], key="edit_loc_sel")
                        if edit_l:
                            # 👤 Utilisateurs présents sur ce site
                            # locs vient de st.session_state['locations'], qui a été fetché avec joinedload(models.Location.users)
                            # On récupère l'objet location frais (car edit_l peut être décalé par rapport à l'API)
                            # Mais locs est déjà là. Cherchons les users.
                            site_users = edit_l.get('users', [])
                            if site_users:
                                st.markdown("###### 👤 Utilisateurs présents sur ce site")
                                df_su = pd.DataFrame(site_users)
                                st.dataframe(df_su[['user_code', 'first_name', 'last_name']], 
                                             column_config={"user_code": "Code", "first_name": "Prénom", "last_name": "Nom"},
                                             hide_index=True, width='stretch')
                            else:
                                st.info("ℹ️ Aucun utilisateur n'est actuellement rattaché à ce site.")

                            st.divider()
                            st.subheader("✏️ Édition des détails")
                            with st.form(f"form_edit_loc_{edit_l['id']}"):
                                c1, c2 = st.columns(2)
                                l_name = c1.text_input("Nom", value=edit_l['name'])
                                l_addr = c2.text_input("Adresse", value=edit_l['address'])
                                c3, c4 = st.columns(2)
                                l_zip = c3.text_input("Code Postal", value=edit_l['zip_code'])
                                l_city = c4.text_input("Ville", value=edit_l['city'])
                                
                                c_save, c_del, _ = st.columns([1, 1, 2])
                                
                                if c_save.form_submit_button("METTRE À JOUR", type="secondary", use_container_width=True):
                                    cb_update_location(edit_l['id'], edit_l['name'], {
                                        "name": l_name,
                                        "address": l_addr,
                                        "zip_code": l_zip,
                                        "city": l_city
                                    })
                                    st.rerun()
                                
                            # Logique de confirmation pour la suppression (hors form)
                            conf_key = f"conf_del_loc_{edit_l['id']}"
                            if st.session_state.get(conf_key):
                                st.warning("Supprimer définitivement ce site ?")
                                col_y, col_n = st.columns(2)
                                if col_y.button("OUI, SUPPRIMER", type="primary", use_container_width=True, key=f"key_yes_{edit_l['id']}"):
                                    cb_location_action("del", edit_l['id'])
                                    st.session_state[conf_key] = False
                                    st.rerun()
                                if col_n.button("ANNULER", key=f"key_no_{edit_l['id']}", use_container_width=True):
                                    st.session_state[conf_key] = False
                                    st.rerun()
                            else:
                                st.markdown('<div class="red-btn">', unsafe_allow_html=True)
                                if st.button("SUPPRIMER LE SITE", type="secondary", use_container_width=True, key=f"btn_del_loc_{edit_l['id']}"):
                                    st.session_state[conf_key] = True
                                    st.rerun()
                                st.markdown('</div>', unsafe_allow_html=True)
            except Exception as e: st.error(f"Erreur Liste Locations: {e}")

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

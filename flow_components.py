# -*- coding: utf-8 -*-
import streamlit as st
import yaml
import json
import uuid
import os
import requests
from engine import check_rules_integrity

# --- CONSTANTES & CONFIGURATION ---
DISPLAY_TO_TECH = {
    'Titre': 'title',
    'Description': 'description',
    'Statut': 'status',
    'Priorité': 'priority',
    'Assigné à': 'assigned_to',
    'Tags': 'tags'
}
TECH_TO_DISPLAY = {v: k for k, v in DISPLAY_TO_TECH.items()}

# Listes strictes pour les Enums
STATUS_OPTIONS = ["Nouveau", "À faire", "En cours", "Terminé"]
PRIORITY_OPTIONS = ["Basse", "Moyenne", "Haute", "Critique"]

ALL_TRIGGER_FIELDS = ["Titre", "Description", "Statut", "Priorité", "Assigné à"]
ALL_ACTION_FIELDS = list(DISPLAY_TO_TECH.keys())

# --- GESTION DE L'ÉTAT (STATE MANAGEMENT) ---

def init_flow_state():
    """Initialise toutes les variables de session nécessaires."""
    defaults = {
        "temp_steps": [],
        "editing_rule_idx": -1,
        "editing_step_idx": -1,
        "current_rule_name": "",
        "current_triggers": [{'field': 'Titre', 'operator': 'Contient', 'value': ''}],
        "buf_fields": [],
        "buf_action": "update",
        "delete_confirm_idx": -1
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

# --- UTILITAIRES DE NORMALISATION ---

def normalize_status(val):
    """Corrige silencieusement les erreurs d'accents courants."""
    if val == "A faire": return "À faire"
    return val

# --- CALLBACKS (LOGIQUE MÉTIER) ---

def cb_clear_buffer():
    """Réinitialise la zone de saisie d'étape."""
    st.session_state.buf_action = "update"
    st.session_state.buf_fields = []
    st.session_state.editing_step_idx = -1

def cb_start_new_rule():
    """Réinitialise tout l'éditeur pour une nouvelle règle."""
    st.session_state.editing_rule_idx = -1
    st.session_state.current_rule_name = ""
    st.session_state.current_triggers = [{'field': 'Titre', 'operator': 'Contient', 'value': ''}]
    st.session_state.temp_steps = []
    cb_clear_buffer()

def cb_add_trigger_condition():
    """Ajoute une condition Trigger en respectant l'exclusion mutuelle."""
    if len(st.session_state.current_triggers) >= 3: return

    # Smart Init : Trouver le premier champ libre
    used_fields = [t.get('field') for t in st.session_state.current_triggers]
    free_fields = [f for f in ALL_TRIGGER_FIELDS if f not in used_fields]
    initial_field = free_fields[0] if free_fields else 'Titre'

    st.session_state.current_triggers.append({
        'field': initial_field, 'operator': 'Contient', 'value': ''
    })

def cb_remove_trigger_condition():
    if len(st.session_state.current_triggers) > 1:
        st.session_state.current_triggers.pop()

def on_trigger_change(idx):
    """Callback : Reset opérateur/valeur quand le champ Trigger change."""
    # Note : Les valeurs sont déjà mises à jour dans le state par le widget via la key
    # On force juste le reset logique
    trig = st.session_state.current_triggers[idx]
    new_field = trig['field'] # La valeur vient d'être mise à jour par le selectbox

    if new_field in ["Statut", "Priorité"]:
        trig['operator'] = "Est égal à"
        trig['value'] = STATUS_OPTIONS[0] if new_field == "Statut" else PRIORITY_OPTIONS[1]
    else:
        trig['operator'] = "Contient"
        trig['value'] = ""

def cb_add_field_row_to_buffer():
    """Ajoute une ligne champ/valeur dans le buffer de l'action."""
    # Exclusion mutuelle locale à l'étape
    used_labels = [row['label'] for row in st.session_state.buf_fields]
    free_labels = [f for f in ALL_ACTION_FIELDS if f not in used_labels]
    
    if not free_labels:
        st.toast("⚠️ Tous les champs possibles sont déjà ajoutés.", icon="info")
        return

    st.session_state.buf_fields.append({
        "id": str(uuid.uuid4())[:8],
        "label": free_labels[0],
        "value": ""
    })

def cb_remove_buffer_row(idx):
    if 0 <= idx < len(st.session_state.buf_fields):
        del st.session_state.buf_fields[idx]

def on_action_label_change(row_id):
    """Callback : Reset valeur quand le label de l'action change."""
    # Retrouver la ligne dans le buffer
    for row in st.session_state.buf_fields:
        if row['id'] == row_id:
            # Récupérer la nouvelle valeur depuis le widget
            new_label = st.session_state.get(f"rule_step_lbl_{row_id}")
            row['label'] = new_label
            
            # Reset smart de la valeur
            if new_label == "Statut":
                row['value'] = STATUS_OPTIONS[0]
            elif new_label == "Priorité":
                row['value'] = PRIORITY_OPTIONS[1]
            elif new_label == "Assigné à":
                # Utilise le premier groupe dispo (ex: "Non assigné")
                s_groups = st.session_state.get('support_groups', ["Non assigné"])
                row['value'] = s_groups[0] if s_groups else ""
            else:
                row['value'] = ""
            
            # Update le widget value pour reflet immédiat
            st.session_state[f"rule_step_val_{row_id}"] = row['value']
            break

def cb_submit_step():
    """Valide et enregistre l'étape du buffer vers la liste temporaire."""
    final_fields = {}
    
    # Récupération des valeurs depuis les widgets via session_state
    for row in st.session_state.buf_fields:
        rid = row['id']
        label = st.session_state.get(f"rule_step_lbl_{rid}", row['label'])
        val = st.session_state.get(f"rule_step_val_{rid}", row['value'])
        
        tech_key = DISPLAY_TO_TECH.get(label, label)
        
        # Normalisation finale
        if label == "Statut": val = normalize_status(val)
        
        final_fields[tech_key] = val

    if not final_fields and st.session_state.buf_action == 'create_task':
         st.toast("❌ Une création de tâche nécessite au moins un champ.", icon="🚨")
         return

    step_obj = {"action": st.session_state.buf_action, "fields": final_fields}
    
    if st.session_state.editing_step_idx != -1:
        st.session_state.temp_steps[st.session_state.editing_step_idx] = step_obj
    else:
        st.session_state.temp_steps.append(step_obj)
    
    cb_clear_buffer()

def cb_load_rule(idx, current_rules):
    """Charge une règle existante pour édition."""
    rule = current_rules[idx]
    st.session_state.editing_rule_idx = idx
    st.session_state.current_rule_name = rule.get('name', '')
    
    # Chargement Triggers (avec support rétro-compatibilité)
    raw_trigs = rule.get('triggers')
    if not raw_trigs:
        raw_trig = rule.get('trigger')
        if isinstance(raw_trig, dict): raw_trigs = [raw_trig]
        else: raw_trigs = [{'field': 'Titre', 'operator': 'Contient', 'value': ''}]
    st.session_state.current_triggers = raw_trigs
    
    # Chargement Étapes
    st.session_state.temp_steps = [s.copy() for s in rule.get('steps', [])]
    cb_clear_buffer()

def cb_load_step_for_edit(idx):
    """Charge une étape dans le buffer."""
    step = st.session_state.temp_steps[idx]
    st.session_state.editing_step_idx = idx
    st.session_state.buf_action = step.get('action', 'update')
    
    fields = step.get('fields', {})
    new_rows = []
    
    for tech_k, v in fields.items():
        label = TECH_TO_DISPLAY.get(tech_k, tech_k)
        # Gestion propre des types
        safe_val = v if v is not None else ""
        if isinstance(safe_val, (dict, list)): safe_val = json.dumps(safe_val)
        else: safe_val = str(safe_val)
        
        new_rows.append({"id": str(uuid.uuid4())[:8], "label": label, "value": safe_val})
    
    st.session_state.buf_fields = new_rows

def cb_delete_rule(idx, workflows_file, api_url):
    """Supprime définitivement une règle."""
    try:
        with open(workflows_file, "r", encoding="utf-8") as f:
            rules = yaml.safe_load(f) or []
        
        if 0 <= idx < len(rules):
            del_name = rules[idx].get('name')
            del rules[idx]
            
            with open(workflows_file, "w", encoding="utf-8") as f:
                yaml.dump(rules, f, default_flow_style=False, allow_unicode=True)
            
            try:
                requests.post(f"{api_url}/audit/logs", json={"message": f"[ADMIN] Règle supprimée: {del_name}"}, timeout=1)
            except: pass
            
            st.toast("🗑️ Règle supprimée.")
            if st.session_state.editing_rule_idx == idx: cb_start_new_rule()
            elif st.session_state.editing_rule_idx > idx: st.session_state.editing_rule_idx -= 1
            
        st.session_state.delete_confirm_idx = -1
    except Exception as e:
        st.error(f"Erreur suppression: {e}")

def cb_save_global_rule(workflows_file, api_url, current_rules):
    """Sauvegarde la règle complète."""
    if not st.session_state.current_rule_name:
        st.toast("❌ Nom de la règle manquant.", icon="🚨")
        return
        
    final_rule = {
        "name": st.session_state.current_rule_name,
        "triggers": st.session_state.current_triggers,
        "steps": st.session_state.temp_steps
    }
    
    if st.session_state.editing_rule_idx != -1:
        current_rules[st.session_state.editing_rule_idx] = final_rule
    else:
        current_rules.append(final_rule)
        
    with open(workflows_file, "w", encoding="utf-8") as f:
        yaml.dump(current_rules, f, default_flow_style=False, allow_unicode=True)
    
    st.toast("✅ Règle sauvegardée avec succès !", icon="💾")
    cb_start_new_rule()

# -----------------------------------------------------------------------------
# INTERFACE PRINCIPALE
# -----------------------------------------------------------------------------
def show_flow_designer(api_url, workflows_file, support_groups=None):
    """Affiche l'interface No-Code du Flow Designer."""
    if support_groups is None:
        support_groups = ["Non assigné"]
    
    init_flow_state()
    st.session_state['support_groups'] = support_groups
    
    # 1. Chargement des règles
    current_rules = []
    if os.path.exists(workflows_file):
        with open(workflows_file, "r", encoding="utf-8") as f:
            current_rules = yaml.safe_load(f) or []

    st.markdown(
        """
        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 24px;">
            <div style="background: linear-gradient(135deg, #10b981 0%, #059669 100%); padding: 10px; border-radius: 10px; display: flex;">
                <span style="font-size: 24px; color: white;">⚙️</span>
            </div>
            <h1 style="margin: 0; font-size: 28px; font-weight: 800; color: #0f172a;">Studio de Configuration des Règles</h1>
        </div>
        """, unsafe_allow_html=True
    )
    
    # --- LISTE DES RÈGLES ---
    with st.expander(f"📚 Règles existantes ({len(current_rules)})", expanded=True):
        if not current_rules:
            st.info("Aucune règle définie.")
        
        for i, rule in enumerate(current_rules):
            # 1. Construction du résumé des déclencheurs
            triggers = rule.get('triggers', [])
            # Gestion rétro-compatibilité (si ancienne règle à trigger unique)
            if not triggers and rule.get('trigger'):
                t = rule.get('trigger')
                triggers = [t] if isinstance(t, dict) else []
            
            # Formatage texte : "Titre Contient 'X' ET Priorité Est égal à 'Haute'"
            desc_parts = []
            for t in triggers:
                if isinstance(t, dict):
                    f = t.get('field', '?')
                    o = t.get('operator', '?')
                    v = t.get('value', '')
                    desc_parts.append(f"<span style='background:#f1f5f9; padding:2px 6px; border-radius:4px; font-weight:600;'>{f}</span> <i style='color:#64748b; font-size:12px;'>{o}</i> <strong style='color:#5048e5;'>'{v}'</strong>")
            
            trigger_summary = " <span style='color:#ef4444; font-weight:800; font-size:11px;'>ET</span> ".join(desc_parts) if desc_parts else "Aucun déclencheur"

            # 2. Affichage en colonnes
            c1, c2, c3 = st.columns([4, 0.5, 0.5])
            
            # Utilisation de Markdown pour un affichage sur deux lignes (Titre gras + Résumé gris)
            with c1:
                st.markdown(f"<p style='margin:0; font-size:16px; font-weight:700; color:#0f172a;'>{i+1}. {rule.get('name')}</p>", unsafe_allow_html=True)
                st.markdown(f"<p style='margin:4px 0 0 0; font-size:13px;'>⚡ Si : {trigger_summary}</p>", unsafe_allow_html=True)

            # Boutons d'action
            c2.button("✏️", key=f"edit_rule_{i}", on_click=cb_load_rule, args=(i, current_rules), help="Modifier la règle")
            
            # Logique de suppression avec confirmation
            if st.session_state.delete_confirm_idx == i:
                st.warning("Supprimer définitivement ?")
                col_yes, col_no = st.columns(2)
                col_yes.button("OUI", key=f"conf_del_rule_{i}", on_click=cb_delete_rule, args=(i, workflows_file, api_url), type="primary")
                col_no.button("NON", key=f"no_rule_{i}", on_click=lambda: st.session_state.update(delete_confirm_idx=-1))
            else:
                c3.button("🗑️", key=f"del_rule_{i}", on_click=lambda x=i: st.session_state.update(delete_confirm_idx=x), help="Supprimer la règle")
            
            st.divider()

    # --- ÉDITEUR ---
    mode = "✨ Nouvelle Règle Automatique" if st.session_state.editing_rule_idx == -1 else "📝 Modification Règle"
    st.markdown(f"<h3 style='margin-top: 2rem; color: #0f172a;'>{mode}</h3>", unsafe_allow_html=True)
    
    c_reset, _ = st.columns([1, 4])
    c_reset.button("🔄 Nouvel éditeur", on_click=cb_start_new_rule)

    st.text_input("Dénomination de la règle", key="current_rule_name", placeholder="ex: Escalade Auto P1...")

    # --- TRIGGER BUILDER (Exclusion Mutuelle Globale) ---
    st.markdown("<h4 style='color: #334155; border-bottom: 2px solid #e2e8f0; padding-bottom: 8px;'>1. Déclencheurs (ET logique)</h4>", unsafe_allow_html=True)
    
    for i, trig in enumerate(st.session_state.current_triggers):
        c1, c2, c3 = st.columns([1.5, 1.5, 2])
        
        # Calcul des options disponibles (Exclusion des autres lignes)
        other_fields = [t['field'] for j, t in enumerate(st.session_state.current_triggers) if j != i]
        valid_fields = [f for f in ALL_TRIGGER_FIELDS if f not in other_fields]
        
        # Fallback si le champ actuel est devenu invalide
        curr_field = trig['field']
        if curr_field not in valid_fields and valid_fields:
            curr_field = valid_fields[0]
            # Mise à jour immédiate du state pour éviter le crash
            st.session_state.current_triggers[i]['field'] = curr_field
            
        # Selectbox Champ (Trigger)
        # Note: on utilise st.session_state.current_triggers[i]['field'] via le key implicite si on veut
        # Mais ici on gère manuellement pour l'exclusion complexe
        new_field = c1.selectbox(f"Champ #{i+1}", valid_fields, index=valid_fields.index(curr_field), key=f"rule_trig_f_{i}")
        
        if new_field != trig['field']:
            trig['field'] = new_field
            on_trigger_change(i) # Reset opérateur/valeur

        # Définition des options d'opérateurs par défaut
        ops = ["Contient", "Ne contient pas", "Est égal à", "Commence par"]

        if new_field == "Statut":
             trig['operator'] = "Est parmi" # Force l'opérateur
             c2.text_input("Opérateur", value="Est parmi", disabled=True, key=f"rule_trig_o_{i}")
             
             # Conversion valeur actuelle en liste si nécessaire
             current_val = trig['value']
             if not isinstance(current_val, list):
                 current_val = [current_val] if current_val and current_val in STATUS_OPTIONS else []
                 
             trig['value'] = c3.multiselect("Valeur", STATUS_OPTIONS, default=current_val, key=f"rule_trig_v_{i}")

        elif new_field == "Priorité":
             trig['operator'] = "Est parmi" # Force l'opérateur
             c2.text_input("Opérateur", value="Est parmi", disabled=True, key=f"rule_trig_o_{i}")
             
             # Conversion valeur actuelle en liste si nécessaire
             current_val = trig['value']
             if not isinstance(current_val, list):
                 current_val = [current_val] if current_val and current_val in PRIORITY_OPTIONS else []

             trig['value'] = c3.multiselect("Valeur", PRIORITY_OPTIONS, default=current_val, key=f"rule_trig_v_{i}")

        elif new_field == "Assigné à":
            trig['operator'] = c2.selectbox("Opérateur", ops, index=0 if trig['operator'] not in ops else ops.index(trig['operator']), key=f"rule_trig_o_{i}")
            if trig['operator'] == "Est égal à":
                # Mode strict avec Selectbox
                try: idx_v = support_groups.index(trig['value'])
                except: idx_v = 0
                trig['value'] = c3.selectbox("Valeur", support_groups, index=idx_v, key=f"rule_trig_v_{i}")
            else:
                # Mode libre (pour 'Contient', 'Commence par'...)
                trig['value'] = c3.text_input("Valeur", value=trig['value'], key=f"rule_trig_v_{i}")
        else:
            # Cas général (Titre, Description...)
            trig['operator'] = c2.selectbox("Opérateur", ops, index=0 if trig['operator'] not in ops else ops.index(trig['operator']), key=f"rule_trig_o_{i}")
            trig['value'] = c3.text_input("Valeur", value=trig['value'], key=f"rule_trig_v_{i}")


    if len(st.session_state.current_triggers) < 3:
        st.button("➕ Ajouter condition", on_click=cb_add_trigger_condition)
    if len(st.session_state.current_triggers) > 1:
        st.button("🗑️ Retirer dernière condition", on_click=cb_remove_trigger_condition)

    st.markdown("<br/>", unsafe_allow_html=True)

    # --- STEP BUILDER (BUFFER) ---
    is_edit_step = st.session_state.editing_step_idx != -1
    title_step = "Modifier l'étape" if is_edit_step else "Ajouter une action"
    st.markdown(f"<h4 style='color: #334155; border-bottom: 2px solid #e2e8f0; padding-bottom: 8px;'>2. Actions : {title_step}</h4>", unsafe_allow_html=True)

    with st.container(border=True):
        # LOGIQUE D'UNICITÉ 'UPDATE' ROBUSTE
        # Vérifie si un update existe déjà AILLEURS que dans l'étape courante
        update_exists = False
        for idx, s in enumerate(st.session_state.temp_steps):
            if s.get('action') == 'update':
                if not is_edit_step: # Si on crée, tout update existant bloque
                    update_exists = True
                elif idx != st.session_state.editing_step_idx: # Si on édite, seul un AUTRE update bloque
                    update_exists = True
        
        act_opts = ['create_task']
        if not update_exists:
            act_opts.insert(0, 'update')
        
        # Forçage de la valeur si l'option actuelle est interdite
        if st.session_state.buf_action not in act_opts:
            st.session_state.buf_action = act_opts[0]
            
        st.selectbox("Type d'action", act_opts, key="buf_action")

        st.caption("Définir les champs concernés :")
        
        # Lignes dynamiques du buffer
        for row in st.session_state.buf_fields:
            rid = row['id']
            c1, c2, c3 = st.columns([2, 2, 0.5])
            
            # Exclusion mutuelle locale à l'étape
            # On prend tous les labels des AUTRES lignes
            other_labels = [r['label'] for r in st.session_state.buf_fields if r['id'] != rid]
            avail_labels = [f for f in ALL_ACTION_FIELDS if f not in other_labels]
            
            # Fallback
            curr_lbl = row['label']
            if curr_lbl not in avail_labels and avail_labels:
                curr_lbl = avail_labels[0]
                row['label'] = curr_lbl # Update interne
                
            # Widget Label
            new_lbl = c1.selectbox("Attribut", avail_labels, index=avail_labels.index(curr_lbl), key=f"lbl_{rid}")
            
            if new_lbl != row['label']:
                row['label'] = new_lbl
                on_action_label_change(rid) # Reset value

            # Widget Valeur
            val_key = f"val_{rid}"
            current_val = row.get('value', '')
            
            if new_lbl == "Statut":
                try: idx_v = STATUS_OPTIONS.index(current_val)
                except: idx_v = 0
                c2.selectbox("Valeur", STATUS_OPTIONS, index=idx_v, key=val_key)
            elif new_lbl == "Priorité":
                try: idx_v = PRIORITY_OPTIONS.index(current_val)
                except: idx_v = 1
                c2.selectbox("Valeur", PRIORITY_OPTIONS, index=idx_v, key=val_key)
            elif new_lbl == "Assigné à":
                try: idx_v = support_groups.index(current_val)
                except: idx_v = 0
                c2.selectbox("Valeur", support_groups, index=idx_v, key=val_key)
            else:
                c2.text_input("Valeur", value=current_val, key=val_key)
            
            # Bouton suppression ligne
            c3.button("🗑️", key=f"rm_row_{rid}", on_click=lambda x=st.session_state.buf_fields.index(row): cb_remove_buffer_row(x))

        # Bouton Ajouter Champ (si dispo)
        if len(st.session_state.buf_fields) < len(ALL_ACTION_FIELDS):
            st.button("➕ Ajouter un champ", on_click=cb_add_field_row_to_buffer)
        
        st.divider()
        cb1, cb2 = st.columns([1, 1])
        cb1.button("✅ Valider l'étape", type="primary", on_click=cb_submit_step)
        if is_edit_step:
            cb2.button("Annuler édition", on_click=cb_clear_buffer)

    # --- LISTE DES ÉTAPES VALIDÉES ---
    st.markdown("<hr style='margin: 30px 0; border-color: #cbd5e1;'/>", unsafe_allow_html=True)
    if st.session_state.temp_steps:
        for idx, step in enumerate(st.session_state.temp_steps):
            act = step['action'].upper()
            
            # Formattage visuel des champs modifiés
            fields_html = []
            for k, v in step['fields'].items():
                fields_html.append(f"<span style='background:#f1f5f9; padding:2px 8px; border-radius:12px; font-size:12px; color:#475569; font-weight:600;'>{k}: <span style='color:#5048e5;'>{v}</span></span>")
            desc_html = " ".join(fields_html)
            
            icon = "🛠️" if act == "UPDATE" else "✨"
            
            with st.container(border=True):
                c1, c2 = st.columns([4, 1])
                c1.markdown(f"**{idx+1}. {icon} {act}**<br/><div style='margin-top:6px;'>{desc_html}</div>", unsafe_allow_html=True)
                c2.button("✏️", key=f"rule_edit_step_{idx}", on_click=cb_load_step_for_edit, args=(idx,))
                c2.button("🗑️", key=f"rule_del_step_{idx}", on_click=lambda x=idx: st.session_state.temp_steps.pop(x))
    
    st.divider()
    st.button("💾 ENREGISTRER LA REGLE", type="primary", use_container_width=True, on_click=cb_save_global_rule, args=(workflows_file, api_url, current_rules))
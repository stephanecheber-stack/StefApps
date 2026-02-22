# -*- coding: utf-8 -*-
import yaml
import os
from sqlalchemy.orm import Session
from models import Task, AuditLog

# Configuration
RULES_FILE = "workflows.yaml"

# Mapping UI -> DB
MAPPING = {
    'Statut': 'status', 
    'Priorité': 'priority', 
    'Assigné à': 'assigned_to', 
    'Titre': 'title', 
    'Description': 'description',
    'Tags': 'tags'
}

# --- FONCTIONS UTILITAIRES (Celles qui manquaient) ---

def normalize_status(val):
    """
    Corrige les variations d'accents pour le statut.
    Utilisé par app.py et engine.py.
    """
    if val == "A faire":
        return "À faire"
    return val

def load_workflows():
    if not os.path.exists(RULES_FILE):
        return []
    try:
        with open(RULES_FILE, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or []
    except Exception as e:
        print(f"[ENGINE] Erreur lecture YAML: {e}")
        return []

def get_task_value(task, field_key):
    """Récupère la valeur d'un champ de la tâche de manière robuste (String)."""
    val = getattr(task, field_key, "")
    # Gestion des Enums SQLAlchemy : si l'objet a un attribut .value, on le prend
    if hasattr(val, "value"):
        val = val.value
    return str(val).strip() if val is not None else ""

def check_condition(task_val, operator, rule_val):
    """Compare la valeur de la tâche avec la règle (Insensible à la casse)."""
    t_val = task_val.lower()
    
    # Cas 1 : La règle est une LISTE (Multi-Select)
    if isinstance(rule_val, list):
        r_vals = [str(v).lower() for v in rule_val]
        if t_val in r_vals:
            return True, f"'{task_val}' est dans {rule_val}"
        return False, f"'{task_val}' PAS dans {rule_val}"

    # Cas 2 : La règle est une CHAINE
    r_val = str(rule_val).lower()
    
    if operator in ['Contient', 'contains']:
        if r_val in t_val: return True, f"'{r_val}' trouvé dans '{task_val}'"
        return False, f"'{r_val}' PAS trouvé dans '{task_val}'"
    
    elif operator in ['Est égal à', 'equals', 'Est parmi']:
        if r_val == t_val: return True, f"'{r_val}' == '{task_val}'"
        return False, f"'{r_val}' != '{task_val}'"
        
    elif operator in ['Commence par', 'starts_with']:
        if t_val.startswith(r_val): return True, f"Début OK"
        return False, f"Début KO"
        
    return False, "Opérateur inconnu"

def cascade_completion(task, db: Session):
    """
    Propagate 'Terminé' status to children.
    """
    # Ensure children are loaded
    if not task.children:
        return

    print(f"[ENGINE] Propagation exclusion 'Terminé' pour parent #{task.id}")
    for child in task.children:
        if child.status != "Terminé": 
            child.status = "Terminé"
            db.add(child)
            # Audit Log
            log = AuditLog(
                task_id=child.id,
                message="[SYSTEME] Clôture automatique (Parent terminé)"
            )
            db.add(log)
            print(f"[ENGINE] -> Enfant #{child.id} clôturé.")
            # Recursive call
            cascade_completion(child, db)

def check_rules_integrity(workflows_file=None):
    """
    Vérifie la validité des règles (Statuts obsolètes, etc.) pour l'interface.
    """
    warnings = []
    # On recharge les règles
    rules = load_workflows()
    
    # Liste de référence des statuts valides
    VALID_STATUSES = ["Nouveau", "À faire", "En cours", "Terminé"]

    for rule in rules:
        rule_name = rule.get('name', 'Sans nom')
        steps = rule.get('steps') or rule.get('actions') or []
        
        for i, step in enumerate(steps):
            fields = step.get('fields', {})
            
            # Vérification du statut
            if 'status' in fields: # ou 'Statut' selon le mapping
                val = fields['status']
                # On tolère 'A faire' car le moteur le corrige à la volée
                if val not in VALID_STATUSES and val != "A faire":
                    warnings.append(f"⚠️ Règle '{rule_name}' (Étape {i+1}) : Statut '{val}' inconnu.")
                    
    return warnings

def process_workflow(task_id, db: Session):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task: return

    print(f"\n[ENGINE] --- Analyse Tâche #{task.id} : {task.title} ---")
    rules = load_workflows()
    
    changes_made = False

    for rule in rules:
        triggers = rule.get('triggers', [])
        # Compatibilité ancienne version (single trigger)
        if not triggers and rule.get('trigger'):
            # Conversion simplifiée
            triggers = [{'field': 'Titre', 'operator': 'Contient', 'value': 'TODO_FIX'}] 

        all_met = True
        
        # --- 1. Vérification des Conditions (ET logique) ---
        for idx, trig in enumerate(triggers):
            field = trig.get('field')
            operator = trig.get('operator')
            rule_value = trig.get('value')
            
            tech_key = MAPPING.get(field)
            if not tech_key: 
                continue

            task_value = get_task_value(task, tech_key)
            is_ok, reason = check_condition(task_value, operator, rule_value)
            
            print(f"[DEBUG] Regle '{rule['name']}' Cond {idx+1}: {field} ({task_value}) {operator} {rule_value} -> {is_ok} ({reason})")
            
            if not is_ok:
                all_met = False
                break
        
        # --- 2. Exécution des Actions ---
        if all_met:
            print(f"[ENGINE] ✅ MATCH pour '{rule['name']}' ! Exécution...")
            
            steps = rule.get('steps') or rule.get('actions') or []
            for step in steps:
                action = step.get('action')
                fields = step.get('fields', {})
                
                if action == 'update':
                    for label, val in fields.items():
                        # Mapping inverse (Label -> Tech) si nécessaire, ou utilisation directe
                        tech_key = MAPPING.get(label) if label in MAPPING else label.lower()
                        
                        # Gestion accent via la fonction utilitaire
                        if tech_key == 'status':
                            val = normalize_status(val)
                        
                        if hasattr(task, tech_key):
                            setattr(task, tech_key, val)
                            print(f"[ENGINE] UPDATE {tech_key} -> {val}")
                            changes_made = True
                            
                            # Check for status completion
                            if tech_key == 'status' and val in ['Terminé', 'Done']:
                                cascade_completion(task, db)
                            
                elif action == 'create_task':
                    # Mapping des champs de création
                    create_data = {}
                    for k, v in fields.items():
                        tk = MAPPING.get(k) if k in MAPPING else k.lower()
                        create_data[tk] = v
                    
                    new_task = Task(
                        title=create_data.get('title', 'Sous-tâche'),
                        description=create_data.get('description', ''),
                        parent_id=task.id,
                        status=create_data.get('status', 'Nouveau'),
                        priority=create_data.get('priority', 'Moyenne'),
                        assigned_to=create_data.get('assigned_to')
                    )
                    db.add(new_task)
                    print(f"[ENGINE] CREATE sous-tâche '{new_task.title}'")
                    changes_made = True

    if changes_made:
        db.commit()
        print("[ENGINE] [OK] Commit effectué.\n")
    else:
        print("[ENGINE] Aucune modification nécessaire.\n")
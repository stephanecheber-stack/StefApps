---
description: Audit_Integrite_LiteFlow
---

# WORKFLOW : AUDIT ET DEBUGGING "LITEFLOW PRO" (V1.0)
# Objectif : Neutraliser les régressions, valider l'intégrité DB/UI et garantir la stabilité du moteur.

[PHASE 1 : AUDIT D'INTÉGRITÉ STRUCTURELLE]
- Vérifier la présence de l'en-tête `# -*- coding: utf-8 -*-` dans tous les fichiers .py (app.py, engine.py, flow_components.py).
- Vérifier l'alignement des Enums de Statut dans models.py, engine.py et app.py. Valeurs autorisées : ["Nouveau", "À faire", "En cours", "Terminé"].
- Vérifier que les variables d'environnement (ADMIN_PASSWORD) sont lues via os.getenv et non codées en dur.
- Valider que requirements.txt contient : fastapi, uvicorn, sqlalchemy, streamlit, pandas, python-dotenv, pyyaml.

[PHASE 2 : CONTRÔLE DES RÉGRESSIONS UI (STREMLIT)]
- Analyser app.py et flow_components.py pour supprimer tout "st.rerun()" situé à l'intérieur d'une fonction de callback (on_click ou on_change).
- Vérifier que le composant st.dataframe du Dashboard utilise bien une clé dynamique basée sur un nonce (ex: key=f"main_grid_{st.session_state.grid_nonce}") pour éviter le bug du double-clic lors des suppressions.
- Vérifier que l'onglet Administration a la case "skip_workflow" cochée par défaut via l'initialisation de la session au moment de l'authentification.
- S'assurer que tous les onglets (st.tabs) utilisent une clé de persistance pour éviter le retour inopiné au Dashboard lors d'une action.

[PHASE 3 : VALIDATION DU MOTEUR DE WORKFLOW (ENGINE.PY)]
- Vérifier que la fonction _evaluate_condition dans engine.py est totalement INSENSIBLE À LA CASSE (utilisation systématique de .lower() sur task_val et rule_val).
- Confirmer que le moteur gère les types hybrides de déclencheurs :
    1. Type LISTE (Multi-select) : utilise l'opérateur "in" pour vérifier si la valeur de la tâche est dans la liste.
    2. Type STRING (Texte libre) : gère les opérateurs "Contient", "Est égal à" et "Commence par".
- Vérifier que la logique de propagation du statut "Terminé" est bien implémentée dans main.py (la clôture d'un parent doit fermer les enfants).
- Vérifier que models.py contient bien la clause cascade="all, delete-orphan" sur la relation parent/enfant des tâches.

[PHASE 4 : MODE RÉPARATION ET AUDIT]
- Si un écart est détecté, appliquer la correction automatique en respectant le pattern "Solid" :
    - Utiliser des Callbacks pour les actions critiques.
    - Utiliser le dictionnaire MAPPING pour transformer les labels UI en colonnes SQL.
- Générer un rapport d'audit dans la console Antigravity listant :
    - [AUDIT-PASS] : Règle respectée.
    - [AUDIT-FIX] : Écart corrigé par l'agent.
    - [AUDIT-WARN] : Point d'attention nécessitant une validation humaine (ex: règles YAML potentiellement incohérentes).

[CONSIGNE FINALE]
Ne jamais supprimer de fonctionnalités existantes. En cas de doute sur une modification de fichier, conserver la logique de "Buffer d'édition" mise en place pour la stabilité de la session Streamlit.
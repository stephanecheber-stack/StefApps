---
description: Audit_Integrite_LiteFlow
---

# WORKFLOW : AUDIT ET DEBUGGING "LITEFLOW PRO" (V2.1 - CORE STABILITY)
# Objectif : Maintenir l'intégrité du noyau, protéger le design Bi-Ton et empêcher les régressions UI.

[PHASE 1 : AUDIT D'INTÉGRITÉ DATA & BACKEND]
- Vérifier l'alignement des fichiers : models.py, schemas.py et main.py.
- Base de Données (models.py) : Confirmer la présence des tables [SupportGroup, Task, AuditLog].
- Intégrité Task : Vérifier la présence impérative des colonnes [id, title, description, priority, status, assigned_to, tags, parent_id, created_at, closed_at].
- Clôture Cascade : Confirmer la présence de 'cascade="all, delete-orphan"' sur la relation 'children' dans models.py.
- API (main.py) : Vérifier que la route PUT /tasks/{id} gère la propagation du statut "Terminé" aux enfants (si applicable) et la date 'closed_at', mais N'APPELLE PAS process_workflow.
- API (main.py) : Vérifier que SEULE la route POST /tasks/ appelle le moteur process_workflow pour l'initialisation.

[PHASE 2 : CONTRÔLE DU DESIGN BI-TON & UI STREMLIT]
- CSS Global : Vérifier l'injection CSS au sommet de app.py (Fond Cloud #f1f5f9, Sidebar Navy #0f172a).
- Standard Boutons : 
    - Bouton Actif (KPI sélectionné) -> type="primary" -> CSS force Vert Foncé #064e3b.
    - Tous les autres boutons -> type="secondary" -> CSS force Bleu SaaS #2563eb + Texte Blanc Gras.
- Stabilité Grille : Vérifier que st.dataframe utilise f"grid_{st.session_state.grid_nonce}" pour garantir le rafraîchissement après suppression.
- Navigation : S'assurer que st.tabs utilise une clé de session pour la persistance de l'onglet actif.
- Sidebar : Vérifier que le titre "CRÉATION" est en blanc gras via la classe CSS 'sidebar-title'.

[PHASE 3 : VALIDATION DU MOTEUR DE WORKFLOW (ENGINE.PY)]
- Normalisation : Vérifier la fonction 'normalize_status' pour la gestion de l'accent sur 'À faire'.
- Robustesse Trigger : Confirmer que _evaluate_condition utilise .lower() et gère :
    1. Les listes (Multi-select) avec l'opérateur 'in'.
    2. Les chaînes (Titre/Description) avec 'Contient', 'Est égal à', etc.
- Protection État Terminal : Vérifier que le moteur possède une sécurité pour ne pas modifier le statut d'un ticket déjà 'Terminé'.
- Logs Terminaux : Utiliser uniquement des préfixes [ENGINE], [DEBUG], [OK] (Pas d'émojis).

[PHASE 4 : MODE AUDIT & RÉPARATION]
- Si Gemini 3 détecte un écart :
    1. Préserver systématiquement les fonctions de Callbacks (cb_...).
    2. Maintenir les noms de statuts en Français uniquement.
    3. Générer un rapport :
       - [PASS] : Fonctionnalité conforme.
       - [FIXED] : Correction automatique appliquée (ex: st.rerun() inutile supprimé).
       - [MANUAL] : Intervention de l'architecte requise.

[CONSIGNE DÉBUTANT]
Toujours expliquer les corrections effectuées de manière pédagogique pour aider l'utilisateur à apprendre la structure de son application.

[PHASE 5 : EXÉCUTION DES TESTS AUTOMATIQUES]
- Lancer la commande : `.\.venv\Scripts\python.exe -m pytest test_suite.py`
- Si un test échoue [FAIL] :
    - Analyser la Traceback.
    - Identifier si c'est une régression UI ou une erreur API.
    - Proposer une correction immédiate AVANT de valider le workflow.
- Si tous les tests passent [PASS] :
    - Confirmer la stabilité de la version.
# DOSSIER DE CONCEPTION PRODUIT (DCP) - LiteFlow Pro

## 1. Résumé Exécutif

**LiteFlow Pro** se positionne comme une alternative "Lite & Solid" aux mastodontes du marché (ServiceNow, Salesforce) pour les PME (50 à 400 employés).
La promesse est simple : apporter la rigueur des processus ITIL sans la lourdeur administrative ni les coûts de licence prohibitifs.

**Points clés de la valeur ajoutée :**
*   **Souveraineté & Simplicité** : Déploiement On-Premise (contrôle total des données), architecture monolithique robuste (SQLite) facile à sauvegarder.
*   **Moteur de Workflow No-Code** : Permet aux équipes opérationnelles de définir leurs propres processus business (Règles, Triggers, Actions) sans écrire une ligne de code.
*   **Maintenance Zéro** : Interface ultra-rapide (Streamlit), mises à jour simplifiées, pas de dépendances cloud complexes.

---

## 2. Architecture Technique

L'application repose sur une stack technologique éprouvée, choisie pour sa stabilité et sa facilité de maintien.

### Stack Technologique
*   **Frontend & Interface** : [Streamlit](https://streamlit.io/) (Python). Choisi pour sa rapidité de développement et son rendu "Data App" natif.
*   **Backend API** : [FastAPI](https://fastapi.tiangolo.com/). Assure la logique métier, la validation des données et la performance via l'asynchronisme.
*   **Base de Données** : [SQLite](https://www.sqlite.org/). Fichier unique (`liteflow.db`), garantissant la portabilité, la simplicité des backups et des performances suffisantes pour la cible PME (< 10k tickets/an).
*   **ORM** : [SQLAlchemy](https://www.sqlalchemy.org/). Gestion propre et sécurisée des interactions BDD.

### Principes de Robustesse Implémentés
1.  **Session State Management** : Utilisation intensive du `st.session_state` pour maintenir le contexte utilisateur (authentification, filtres, buffers d'édition) entre les rechargements de page.
2.  **Pattern "Key Rotation"** : Pour forcer le rafraîchissement propre des composants complexes (comme la grille de données `st.dataframe`) lors d'une action de suppression ou de mise à jour, un "nonce" (`grid_key`) est incrémenté. Cela garantit que l'interface reflète toujours l'état exact de la base de données.
3.  **Callbacks Transactionnels** : Les actions critiques (Création, Update, Delete) sont encapsulées dans des fonctions de callback (`cb_create_task`, `cb_delete_task`) qui gèrent l'appel API, la notification utilisateur (`st.toast`), et le nettoyage de l'état local en une seule transaction logique.

---

## 3. Modèle de Données Relationnel

Le modèle de données est conçu pour être extensible tout en restant lisible.

### 3.1 Tables de Fondation (Actuel & Cible)

Actuellement, l'authentification est simplifiée (Code Admin unique), mais le modèle prévoit l'extension vers une gestion fine des identités.

| Table | Description | Champs Clés (Cible) | Implémenté |
| :--- | :--- | :--- | :---: |
| **Users** | Identités des acteurs (Techniciens, Requérants) | `id`, `username`, `email`, `role`, `sso_id` | ❌ (Global Admin) |
| **SupportGroups** | Équipes de résolution (Support N1, Réseau...) | `id`, `name`, `email_alias` | ✅ (`name` unique) |
| **Locations** | Sites physiques (Siège, Usine, Agence) | `id`, `name`, `address`, `country` | ❌ (Cible) |
| **Credentials** | Coffre-fort pour automatisations | `id`, `name`, `type` (SSH/API), `encrypted_val` | ❌ (Env Var) |

### 3.2 Tâches (Cœur du Système)

La table `Task` est centrale et polymorphe (Incident, Demande, Changement).

**Structure `tasks` :**
*   `id` (PK) : Identifiant unique.
*   `title`, `description` : Données textuelles.
*   `status` : Enum (`Nouveau`, `À faire`, `En cours`, `Terminé`).
*   `priority` : Niveau d'urgence (`Basse`, `Moyenne`, `Haute`, `Critique`).
*   `assigned_to` : Lien vers le Groupe (String actuellement, FK vers `SupportGroup` en cible).
*   **Hiérarchie** :
    *   `parent_id` (FK) : Permet de lier une sous-tâche à une tâche mère.
    *   *Cascade Delete* : La suppression d'un parent entraîne celle des enfants (via `relationship(cascade="all, delete-orphan")`).

### 3.3 CMDB Allégée (Assets)

*Architecture Cible pour la version "Pro"*
Une table `Assets` liée aux Tâches pour tracer les équipements impactés.

**Structure cible `assets` :**
*   `id` (PK), `name` (Nom Hôte), `serial_number`.
*   `status` (En service, En stock, Rebut).
*   `location_id` (FK vers Locations).
*   `assigned_user_id` (FK vers Users).

---

## 4. Moteur de Workflow (Flow Designer)

Le moteur (`engine.py` et `flow_components.py`) permet l'automatisation sans code.

### 4.1 Constructeur No-Code
*   **Trigger Builder** : Interface permettant de définir des conditions de déclenchement multiples.
    *   **Logique** : Les conditions sont cumulatives (ET Logique).
    *   **Opérateurs** : `Contient`, `Est égal à`, `Commence par`, `Est parmi` (pour les listes).
    *   *Exemple* : SI `Titre` contient "Panne" ET `Priorité` est "Critique".

### 4.2 Typologie des Actions
Une règle peut déclencher une séquence d'actions (`WorkflowStep`).
1.  **Update** : Modification d'un champ de la tâche courante (ex: Passer le statut à `En cours`, Assigner au groupe `Support N2`).
2.  **Create Task** : Génération automatique d'une tâche enfant (ex: "Commander pièce de rechange") liée au parent.
3.  **Approbation** (Roadmap) : Suspension du flux en attente d'une validation.

### 4.3 Logique d'Exécution
*   **Trigger Evaluation** : À chaque création/modification de ticket, le moteur scanne toutes les règles actives.
*   **Step Execution** : Si les triggers matchent, les actions sont exécutées séquentiellement.
*   **Cascade Completion** : Une logique récursive détecte si toutes les sous-tâches sont terminées pour potentiellement clore le dossier parent (logique programmable).

---

## 5. Expérience Utilisateur (UX)

L'UX est conçue pour la productivité ("High Information Density").

*   **Philosophie "Data Grid"** : Le Dashboard n'est pas une suite de cartes aérées mais un tableau dense (`st.dataframe`) permettant le tri, le filtrage et la sélection rapide.
*   **Édition "Buffer"** :
    *   Pour la création de règles : On "prépare" les étapes dans une zone tampon avant de les valider dans le flux principal. Cela évite les erreurs de saisie et permet de revenir en arrière.
    *   Pour l'édition de ticket : Les champs ne sont sauvegardés que sur action explicite ("Enregistrer"), permettant de modifier plusieurs attributs sans appels API incessants.
*   **Dashboard Opérationnel** : Vue consolidée avec recherche instantanée et indicateurs visuels (Badges de couleur pour Statuts/Priorités).

---

## 6. Sécurité & Maintenance

*   **Gestion des Accès** :
    *   Actuel : Code Admin unique séquestré dans une variable d'environnement (`ADMIN_PASSWORD`).
    *   Interface : Sidebar verrouillée par défaut, déverrouillage de session (`st.session_state.authenticated`).
*   **Auditabilité** :
    *   Table `AuditLog` : Trace les actions systèmes (règles déclenchées, suppressions).
    *   Traçabilité : Chaque modification automatique par le moteur est loggée ("Clôture automatique", "Règle X appliquée").
*   **Souveraineté** :
    *   Données stockées localement (fichier `.db`), pas de fuite vers le cloud.
    *   Indépendance totale d'internet pour le fonctionnement interne.

---

## 7. Roadmap Évolutive

Les prochaines étapes pour passer de la version "Lite" à "Pro" :

1.  **Module Logistique (Assets)** : Création de la vue CMDB complète et lien avec les tickets (Champ "Asset Impacté").
2.  **Portail Self-Service** : Interface simplifiée pour les utilisateurs finaux (Création de ticket simple, Suivi).
3.  **Transition Cloud Optionnelle** : Conteneurisation (Docker) de l'application pour déploiement sur Azure/AWS si le client le souhaite, tout en gardant la base SQLite ou bascule vers PostgreSQL sans changer le code métier (grâce à SQLAlchemy).

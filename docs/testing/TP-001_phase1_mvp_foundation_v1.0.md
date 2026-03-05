# TP-001 — Plan de test (Phase 1 / MVP Foundation)

- **Référence document** : TP-001
- **Version** : v1.0
- **Statut** : Prêt à exécuter
- **Projet** : Application RAG single-tenant (FastAPI + SQL Server + Next.js)
- **Auteur** : QA/Validation
- **Date** : 2026-03-05

---

## 1) Objectifs du plan de test

Valider, pour la **Phase 1 (fondations MVP)**, que les capacités de base backend et data sont robustes, traçables et compatibles avec un contexte d’entreprise/réglementé :

1. Démarrage backend FastAPI sans erreur critique.
2. Exposition et fiabilité des endpoints de santé.
3. Chargement de configuration (fichiers + variables d’environnement) et gestion correcte des erreurs.
4. Connectivité Microsoft SQL Server (authentification, timeout, panne contrôlée).
5. Migrations Alembic (init/upgrade/downgrade) avec vérification d’idempotence.
6. Conformité du schéma de base de données (tables/contraintes/index) :
   - `users`
   - `roles` / `permissions` (ou équivalent)
   - `documents_metadata`
   - `index_state`
   - `audit_events`
7. Journalisation basique et écriture d’événements d’audit (si inclus dans le périmètre effectif du lot).
8. Baseline sécurité : absence de secrets en dépôt et validation stricte de configuration.

---

## 2) Périmètre

### 2.1 Dans le périmètre (In Scope)

- Backend FastAPI (startup/shutdown, health checks, dépendances DB).
- Couche config (env, `.env`, paramètres invalides/manquants).
- SQL Server (connectivité et erreurs connues).
- Alembic (cycle de migration complet + rollback de contrôle).
- Vérification structurelle de schéma SQL.
- Vérification logs techniques et audit minimal.
- Contrôles de sécurité de base pour la phase fondation.

### 2.2 Hors périmètre (Out of Scope)

- Flux fonctionnels complets RAG (indexation avancée, ranking, QA finale).
- UI/UX frontend Next.js (hors disponibilité applicative si nécessaire).
- Tests de performance, charge, résilience distribuée multi-noeuds.
- Scénarios IAM avancés (SSO/OIDC), SIEM export complet, multi-tenant.

---

## 3) Hypothèses et dépendances

1. Une instance SQL Server accessible est disponible (local conteneurisé ou environnement partagé).
2. Le projet contient une configuration Alembic opérationnelle.
3. Les variables d’environnement minimales sont documentées.
4. Les droits DB permettent création/modification d’objets dans un schéma de test dédié.
5. Les journaux applicatifs sont accessibles (console, fichier, ou agrégateur local).

---

## 4) Pré-requis environnement de test

## 4.1 Pré-requis communs

- Code source synchronisé sur la version cible (tag/commit release candidat).
- Python + dépendances backend installées.
- Outil de requête SQL (sqlcmd, Azure Data Studio, DBeaver, etc.).
- Accès au fichier de configuration et variables d’environnement.
- Horloge système synchronisée (important pour corrélation audit/log).

## 4.2 Notes Windows

- Vérifier pilotes ODBC SQL Server compatibles.
- Attention aux séparateurs de chemins, encodage UTF-8 et fins de ligne.
- Exécuter shell PowerShell en mode standard (pas de privilèges admin non requis).

## 4.3 Notes Linux

- Vérifier librairies client SQL Server (`msodbcsql`, `unixODBC`) selon le driver utilisé.
- Vérifier permissions de lecture des fichiers `.env`/secrets.
- Normaliser timezone locale (UTC recommandé pour audit).

---

## 5) Données de test

### 5.1 Jeux de données minimaux

- **Utilisateur admin de test** (actif).
- **Rôle(s) de base** : `admin`, `reader` (ou équivalents).
- **Permissions minimales** associées.
- **Document metadata factice** (1 enregistrement valide).
- **Etat d’index** (1 enregistrement initial, statut attendu ex. `pending`/`ready`).
- **Evénements audit** : un événement `startup` et un événement `health_check` (si applicable).

### 5.2 Règles de gestion des données

- Aucune donnée réelle client/PII.
- Données déterministes et rejouables.
- Nettoyage post-test défini (rollback migration ou script cleanup).

---

## 6) Approche de test

## 6.1 Niveaux de test

1. **Tests unitaires** (si présents) : validation parsing config, validateurs, helpers DB.
2. **Tests d’intégration** : backend + DB + migrations + écriture audit.
3. **Tests API** : endpoints `/health` et dérivés, codes HTTP, latence cible.
4. **Contrôles manuels ciblés** : logs, inspection schéma SQL, vérification secrets dans repo.

## 6.2 Stratégie d’exécution progressive

1. Pré-check environnement.
2. Démarrage backend sans DB (si scénario supporté) puis avec DB.
3. Validation config nominale puis erreurs de config.
4. Cycle migrations complet.
5. Validation schéma SQL.
6. Validation logs/audit.
7. Contrôles sécurité baseline.
8. Consolidation des preuves + rapport TR-001.

## 6.3 Critères qualité minimum (Go/No-Go)

- 100% des cas critiques P1 en **PASS**.
- 0 défaut bloquant en startup/config/DB/migrations.
- Toute non-conformité sécurité critique = **No-Go**.

---

## 7) Critères d’entrée / sortie

## 7.1 Critères d’entrée

- Build/branche stable disponible.
- Variables d’environnement de test connues et chargées.
- DB de test disponible et accessible.
- Migrations versionnées présentes.
- Plan TP-001 revu/validé par QA + lead technique.

## 7.2 Critères de sortie

- Exécution de tous les cas TP-001.
- Rapport TR-001 complété avec statut global.
- Preuves archivées (logs, captures, requêtes SQL exportées).
- Anomalies consignées avec sévérité/priorité.
- Décision formelle Go / Go conditionnel / No-Go.

---

## 8) Risques et mitigations

| Risque | Impact | Probabilité | Mitigation |
|---|---:|---:|---|
| Instabilité SQL Server de test | Elevé | Moyen | Environnement de secours + tests rejouables |
| Drift de schéma entre branches | Elevé | Moyen | Vérification `alembic current/history` avant exécution |
| Config non homogène Windows/Linux | Moyen | Moyen | Matrice d’env + checklist OS dédiée |
| Logs insuffisants pour audit | Elevé | Faible/Moyen | Renforcer niveau log minimal + corrélation horodatée |
| Secrets exposés accidentellement | Critique | Faible | Scan automatique repo + revue manuelle systématique |

---

## 9) Cas de test détaillés (Phase 1)

> Convention ID : `TC-P1-XXX` ; priorité `P1/P2/P3`.

### TC-P1-001 — Démarrage backend nominal
- **Priorité** : P1
- **Préconditions** : Variables minimales valides ; DB accessible.
- **Etapes** :
  1. Lancer le backend FastAPI.
  2. Observer logs startup.
  3. Vérifier état process.
- **Résultats attendus** :
  - Service démarré sans exception bloquante.
  - Log de démarrage présent avec niveau attendu.
- **Preuves** : extrait logs startup + timestamp.

### TC-P1-002 — Endpoint health principal
- **Priorité** : P1
- **Préconditions** : Backend démarré.
- **Etapes** :
  1. Appeler endpoint de santé (ex. `/health`).
  2. Mesurer code HTTP et payload.
- **Résultats attendus** : HTTP 200, statut explicite (`ok`/`healthy`), temps de réponse conforme seuil projet.
- **Preuves** : sortie `curl`/Postman + capture timestamp.

### TC-P1-003 — Health avec dépendance DB indisponible
- **Priorité** : P1
- **Préconditions** : Backend configuré avec vérification DB ; simuler DB down.
- **Etapes** :
  1. Couper accès DB (service stoppé ou credentials invalides temporaires).
  2. Appeler endpoint santé dépendant DB.
- **Résultats attendus** : statut dégradé explicite (code/JSON cohérent), absence de crash backend.
- **Preuves** : logs erreur contrôlée + réponse API.

### TC-P1-004 — Chargement configuration nominale
- **Priorité** : P1
- **Préconditions** : Fichier env/config complet.
- **Etapes** :
  1. Charger config au démarrage.
  2. Vérifier que les clés obligatoires sont reconnues.
- **Résultats attendus** : démarrage OK, aucune valeur critique manquante.
- **Preuves** : logs init config (sans fuite de secret).

### TC-P1-005 — Configuration invalide (clé requise absente)
- **Priorité** : P1
- **Préconditions** : Retirer une variable obligatoire.
- **Etapes** :
  1. Lancer backend avec config incomplète.
- **Résultats attendus** : échec contrôlé au startup, message explicite, code retour non nul.
- **Preuves** : logs d’erreur + console.

### TC-P1-006 — Configuration invalide (format incorrect)
- **Priorité** : P1
- **Préconditions** : Injecter valeur invalide (port non numérique, bool mal formé...).
- **Etapes** : démarrer l’application.
- **Résultats attendus** : validation de schéma config rejette la valeur, diagnostic exploitable.
- **Preuves** : trace validation.

### TC-P1-007 — Connectivité SQL Server nominale
- **Priorité** : P1
- **Préconditions** : DB accessible, credentials valides.
- **Etapes** :
  1. Démarrer backend.
  2. Exécuter une requête simple de vérification via l’app ou client SQL.
- **Résultats attendus** : connexion établie, pas d’erreur d’auth/timeout.
- **Preuves** : logs connexion + résultat requête (`SELECT 1`).

### TC-P1-008 — Connectivité SQL Server (credentials invalides)
- **Priorité** : P1
- **Préconditions** : mot de passe volontairement incorrect.
- **Etapes** : lancer backend.
- **Résultats attendus** : échec contrôlé avec message non sensible (pas de secret en clair).
- **Preuves** : logs d’erreur sanitizés.

### TC-P1-009 — Alembic init/current/history
- **Priorité** : P1
- **Préconditions** : configuration Alembic prête.
- **Etapes** :
  1. Vérifier `current`.
  2. Vérifier `history`.
- **Résultats attendus** : chaîne de migrations cohérente et traçable.
- **Preuves** : sorties commandes Alembic.

### TC-P1-010 — Alembic upgrade head
- **Priorité** : P1
- **Préconditions** : base vierge/schéma de test.
- **Etapes** : exécuter migration vers `head`.
- **Résultats attendus** : toutes tables cibles créées, aucune erreur SQL.
- **Preuves** : logs migration + snapshot schéma.

### TC-P1-011 — Alembic downgrade contrôlé puis upgrade
- **Priorité** : P1
- **Préconditions** : base au `head`.
- **Etapes** :
  1. Downgrade d’une révision.
  2. Re-upgrade vers `head`.
- **Résultats attendus** : rollback appliqué puis restauration complète sans incohérence.
- **Preuves** : sorties commandes + comparaison schéma avant/après.

### TC-P1-012 — Idempotence migrations
- **Priorité** : P1
- **Préconditions** : base déjà à `head`.
- **Etapes** : rejouer upgrade vers `head`.
- **Résultats attendus** : aucune modification destructive inattendue, exécution sans erreur.
- **Preuves** : logs commande + état version inchangé.

### TC-P1-013 — Validation table `users`
- **Priorité** : P1
- **Préconditions** : migrations appliquées.
- **Etapes** : inspecter colonnes, PK, contraintes d’unicité/index attendus.
- **Résultats attendus** : structure conforme au modèle de données phase 1.
- **Preuves** : requête dictionnaire SQL + export résultat.

### TC-P1-014 — Validation `roles` / `permissions`
- **Priorité** : P1
- **Préconditions** : migrations appliquées.
- **Etapes** : vérifier tables, FK, table de mapping (si applicable).
- **Résultats attendus** : intégrité référentielle correcte.
- **Preuves** : requêtes SQL + schéma relationnel.

### TC-P1-015 — Validation `documents_metadata`
- **Priorité** : P1
- **Préconditions** : migrations appliquées.
- **Etapes** : vérifier colonnes techniques, contraintes nullabilité, index de recherche.
- **Résultats attendus** : conformité au design minimal ingestion documentaire.
- **Preuves** : requête metadata + plan index.

### TC-P1-016 — Validation `index_state`
- **Priorité** : P1
- **Préconditions** : migrations appliquées.
- **Etapes** : vérifier structure et contraintes de statut.
- **Résultats attendus** : table exploitable pour suivi pipeline indexation.
- **Preuves** : résultat requête inspection.

### TC-P1-017 — Validation `audit_events`
- **Priorité** : P1
- **Préconditions** : table incluse dans phase 1.
- **Etapes** : contrôler colonnes (type, actor, action, timestamp, payload minimal).
- **Résultats attendus** : schéma audit conforme et horodatage non nul.
- **Preuves** : requête dictionnaire SQL.

### TC-P1-018 — Ecriture d’un événement d’audit applicatif
- **Priorité** : P1
- **Préconditions** : mécanisme audit activé.
- **Etapes** : déclencher action connue (startup/health/admin test).
- **Résultats attendus** : ligne audit persistée avec corrélation log/API.
- **Preuves** : log applicatif + `SELECT` sur `audit_events`.

### TC-P1-019 — Vérification niveau de logs minimal
- **Priorité** : P2
- **Préconditions** : backend démarré.
- **Etapes** : générer cas nominal + erreur contrôlée.
- **Résultats attendus** : niveau INFO/ERROR cohérent, pas de stacktrace sensible en nominal.
- **Preuves** : extrait logs.

### TC-P1-020 — Baseline sécurité : secrets dans le dépôt
- **Priorité** : P1
- **Préconditions** : accès repo local.
- **Etapes** : scanner dépôt (patterns secrets) + revue fichiers config exemple.
- **Résultats attendus** : aucun secret actif/versionné.
- **Preuves** : rapport de scan + check manuel.

### TC-P1-021 — Baseline sécurité : absence de fuite secret en logs
- **Priorité** : P1
- **Préconditions** : lancer scénarios d’erreur config/DB.
- **Etapes** : inspecter logs produits.
- **Résultats attendus** : mots de passe/tokens non affichés en clair.
- **Preuves** : extraits logs masqués.

### TC-P1-022 — Robustesse arrêt/redémarrage service
- **Priorité** : P2
- **Préconditions** : backend en fonctionnement.
- **Etapes** : effectuer cycle stop/start rapide.
- **Résultats attendus** : redémarrage propre, pas de verrou DB persistant.
- **Preuves** : logs shutdown/startup + health success.

---

## 10) Exigences de traçabilité & preuves

- Associer chaque test case à :
  - une preuve horodatée,
  - l’environnement (OS, version Python, commit, DB version),
  - un statut (`PASS`, `FAIL`, `BLOCKED`, `NOT RUN`).
- Stocker les preuves sous : `docs/testing/evidence/TP-001/<date-run>/`.
- Nommer les captures/logs avec l’ID de test case.

---

## 11) Workflow documentaire progressif (jalons futurs)

### 11.1 Règle de production documentaire par milestone

A chaque nouveau lot fonctionnel, produire :
1. Un nouveau plan de test **TP-00X**.
2. Un rapport d’exécution **TR-00X** (basé sur template TR-001).
3. Une mise à jour du **Master Test Index**.

### 11.2 Lots recommandés

- TP-002 : Authentification / RBAC
- TP-003 : Upload documentaire
- TP-004 : Indexation + vector store
- TP-005 : Requête RAG
- TP-006 : Strict Document Scope
- TP-007 : Dashboard admin
- TP-008 : Audit avancé / export SIEM
- TP-009 : Déploiement & scripts opérationnels

### 11.3 Convention de nommage/versionning

- **Plans** : `TP-00X_<milestone>_vMAJOR.MINOR.md`
- **Rapports** : `TR-00X_<milestone>_runYYYYMMDD_vMAJOR.MINOR.md`
- **Index master** : `docs/testing/master_test_index.md`

Exemples :
- `TP-002_auth_rbac_v1.0.md`
- `TR-002_auth_rbac_run20260410_v1.0.md`

### 11.4 Arborescence recommandée repo

- `docs/testing/master_test_index.md`
- `docs/testing/TP-001_phase1_mvp_foundation_v1.0.md`
- `docs/testing/templates/TR-001_test_report_template_v1.0.md`
- `docs/testing/reports/`
- `docs/testing/evidence/`

---

## 12) Gouvernance qualité (recommandée)

- Revue croisée QA + Tech Lead obligatoire avant exécution.
- Signature de validation de sortie en fin de TR.
- Conservation des preuves selon politique conformité interne.

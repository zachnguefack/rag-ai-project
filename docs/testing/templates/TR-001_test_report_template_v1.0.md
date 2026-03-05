# TR-001 — Modèle de rapport d’exécution de tests

- **Référence rapport** : TR-001
- **Version template** : v1.0
- **Lié au plan** : TP-00X

---

## 1) Informations générales

- **Projet** :
- **Milestone / Phase** :
- **Plan de test de référence** :
- **Version applicative testée (commit/tag)** :
- **Environnement** : DEV / QA / PREPROD
- **Date d’exécution** :
- **Equipe exécutante** :
- **Relecteurs** :

---

## 2) Résumé exécutif

- **Statut global** : GO / GO conditionnel / NO-GO
- **Couverture exécutée** : XX% (cas exécutés / cas planifiés)
- **Cas PASS** :
- **Cas FAIL** :
- **Cas BLOCKED** :
- **Cas NOT RUN** :
- **Défauts critiques ouverts** :
- **Décision recommandée** :

---

## 3) Matrice des résultats par test case

| Test Case ID | Statut | Sévérité si échec | Ticket anomalie | Commentaires | Preuve |
|---|---|---|---|---|---|
| TC-P1-001 | PASS/FAIL/BLOCKED/NOT RUN | Critique/Majeure/Mineure | BUG-xxx |  | lien fichier |

---

## 4) Détails des anomalies

Pour chaque anomalie :
- **ID anomalie** :
- **Test Case lié** :
- **Description** :
- **Comportement attendu** :
- **Comportement observé** :
- **Sévérité / Priorité** :
- **Reproductibilité** : Toujours / Intermittent
- **Environnement** :
- **Preuves** : logs, captures, requêtes SQL
- **Statut** : Ouvert / Corrigé / Re-test en attente / Fermé

---

## 5) Preuves collectées

- **Chemin d’archivage** : `docs/testing/evidence/<TP-ID>/<date-run>/`
- **Liste** :
  - Logs backend
  - Captures réponses API
  - Exports requêtes SQL
  - Captures écran (si applicable)

---

## 6) Evaluation des risques résiduels

| Risque résiduel | Impact | Probabilité | Décision / Action |
|---|---:|---:|---|
|  |  |  |  |

---

## 7) Conclusion et décision qualité

- **Conclusion QA** :
- **Conditions de mise en production (si GO conditionnel)** :
- **Actions post-test requises** :

---

## 8) Sign-off

- **QA Lead** (nom, date, signature) :
- **Tech Lead** (nom, date, signature) :
- **Product Owner / Responsable métier** (nom, date, signature) :

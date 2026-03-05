# Master Test Index

## Objectif
Centraliser l’inventaire des plans et rapports de test par milestone, leur statut et leur traçabilité.

## Convention documentaire
- Plans : `TP-00X_<milestone>_vMAJOR.MINOR.md`
- Rapports : `TR-00X_<milestone>_runYYYYMMDD_vMAJOR.MINOR.md`
- Templates : `docs/testing/templates/`
- Preuves : `docs/testing/evidence/<TP-ID>/<date-run>/`

## Registre des plans de test

| ID | Milestone | Fichier plan | Statut plan | Dernier rapport | Statut global exécution |
|---|---|---|---|---|---|
| TP-001 | Phase 1 — MVP foundation | `docs/testing/TP-001_phase1_mvp_foundation_v1.0.md` | Actif | À produire | Non exécuté |
| TP-002 | Auth / RBAC | À créer | Planifié | N/A | N/A |
| TP-003 | Upload documentaire | À créer | Planifié | N/A | N/A |
| TP-004 | Indexation / Vector store | À créer | Planifié | N/A | N/A |
| TP-005 | Requête RAG | À créer | Planifié | N/A | N/A |
| TP-006 | Strict Document Scope | À créer | Planifié | N/A | N/A |
| TP-007 | Dashboard Admin | À créer | Planifié | N/A | N/A |
| TP-008 | Audit avancé / SIEM export | À créer | Planifié | N/A | N/A |
| TP-009 | Déploiement / scripts ops | À créer | Planifié | N/A | N/A |

## Workflow de mise à jour
1. Créer TP du milestone au démarrage de lot.
2. Exécuter et générer TR correspondant.
3. Mettre à jour ce registre (statuts + liens).
4. Archiver les preuves au chemin normalisé.

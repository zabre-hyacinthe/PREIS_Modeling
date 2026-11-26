# PREIS-Modeling v3 — tracker des modélisations épidémiques en Afrique

Qui, où, quand, quel modèle, quel degré de preuve. Origine : PREIS V10 (lecture seule, D:\PREIS_V10_March_4_26). Version 26 nov. 2026.

## Pipeline (Windows : `run_all.bat`)
1. `tracker/fetch_europepmc.py` — Europe PMC (REST, resultType=core) : auteurs, affiliations, pays d'affiliation, DOI, type, dates, citations, préprints (SRC:PPR, exclus par V10). Incrémental (`--since`). Brut conservé dans `results/raw/`. NON testé sur le réseau réel (injoignable depuis la VM) : parseur testé sur données simulées ; premier lancement à surveiller.
2. `tracker/build_tracker.py` — règles lisibles (`rules.py`), dédoublonnage, classe de modèle, pathogène, pertinence Afrique, année cible, degré de preuve, suivi de réalisation, statut de revue.
3. `tracker/export_hub.py` — `hub_export/modeling_preis_series.csv` (contrat HUB 14 colonnes, module `modeling`) et `modeling_register.csv` (registre qui/où/quand/preuve).
Sans le fetch, le build utilise V10 `articles.csv` (corpus 2024-2026, sans auteurs, daté du 4 mai 2026).

## Degré de preuve (provisoire : titre+résumé)
T0 hors modélisation · T1 secondaire (revue, commentaire, cadre) · T2 modèle sans validation signalée · T3 validation interne/calibration · T4 validation externe, prospective ou prévision confrontée aux observations / multi-modèles. Score de transparence 0-5 (validation, incertitude, code, données, hypothèses). Fondements : EPIFORGE 2020 ; PROBAST+AI / TRIPOD+AI 2025 ; Chaturvedi et al., BMC Infect Dis 2025 (aucun guide unique pour les modèles de maladies infectieuses) ; Bracher et al. 2021 (WIS). Le texte intégral (code ouvert, validation) doit confirmer le niveau pour les articles en accès ouvert (étape à ajouter).

## Statut de revue
`retenu (règles, non validé humain)` · `candidat à revoir (humain)` (modèle détecté mais confiance faible : rien n'est perdu) · `hors périmètre`. Au 26 nov. : 151 retenus, 132 candidats sur 4 985 articles.

## Validation (honnête)
- 200 articles stratifiés (A cœur Afrique 70, B autre 25, C quasi-exclus 65, D hasard 40) + 160 articles supplémentaires de la strate D. Relecteurs : 3 IA indépendants (modélisateur, évaluateur de preuves, praticien Africa CDC) puis 2 IA pour la strate D. Kappa de Fleiss 0,79–0,93 (est-ce un modèle 0,92 ; infectieux 0,93 ; classe 0,89 ; Afrique 0,79 ; preuve 0,80) : accord élevé mais relecteurs corrélés et résumés en partie tronqués → ce n'est pas un étalon.
- Tracker « retenu » : précision ≈ 0,67 ; rappel ≈ 0,49 (≈ 0,34–0,7 selon le taux, très incertain, de modèles dans les articles sans terme de modélisation : 3/200). Avec la file de candidats, rappel ≈ 0,6 (0,4–0,9).
- Les règles ont été ajustées après la première évaluation : ces chiffres sont optimistes. Étalon-or humain requis (`docs/PANEL_EXPERTS.md`) : 200 articles minimum, 2 relecteurs + arbitre ; `python tests/agreement.py pack/labels`.
- Aucune statistique publiable avant ce panel.

## Limites
Un seul index (Europe PMC) ; résumés seulement ; classification par règles (anglais) ; pertinence Afrique par texte ; préprints non évalués par les pairs ; pas de suivi de réalisation automatisé (statut « à vérifier » = file humaine).

## Prochaines étapes
Lancer le fetch ; panel humain ; extension texte intégral OA (code/validation) ; classifieur supervisé entraîné sur l'étalon humain ; cartes RCC (49/54 pays dans V10, ne pas inventer) ; planification quotidienne ; adaptateur `modeling` dans hub_sync.py ; relier à AI Tracker (ingestion commune).

## Planification et alertes (ajout 26 nov.)
- Planification : GitHub Actions (`.github/workflows/preis_modeling.yml`, 05:30 UTC), comme PREIS Polio ; mêmes mécanismes de sécurité que PREIS AI (simulation par défaut, secrets, paliers, journal anti-doublons, baseline à la première exécution réelle). Mise en ligne : `INSTRUCTIONS_GITHUB.txt`.
- Alertes : `tracker/build_alerts.py` (règles dans `config/alert_rules.json`, raisons affichées pour chaque score) ; envoi : `tracker/send_alerts.py`.
- Contrôle humain minimal avant l'envoi réel : `pack/AUDIT_EXPRESS_30_retenus.csv` (30 articles retenus, 20 minutes).
- Filtre par type de publication (revue, éditorial, commentaire, lettre) actif après le premier fetch Europe PMC.

## Validation historique et suivi de realisation (backtest)

- Module : `tracker/backtest.py` ; tests : `tests/test_backtest.py` (donnees synthetiques uniquement).
- Entree : `config/prediction_records.csv` (une ligne = une prediction : cible, pays, date de prediction,
  date d'arret des donnees, periode cible, valeur/intervalle/probabilite, scenario conditionnel,
  groupe, prevision de reference, valeur observee + source).
- Sorties : `data/backtest/backtest_scored.csv` et `backtest_report.json` (par maladie et classe de modele).
- Regles : prediction posterieure au debut de la periode cible = invalide ; scenario conditionnel non juge
  tant que les hypotheses ne sont pas verifiees ; pas de source = non evaluable.
- Seuils (confirmee 2/3 a 1,5 ; partielle 0,5 a 2 ; ou observe dans l'intervalle) = PROPOSITIONS, a valider par le panel.
- La liste de cas doit etre constituee par regle (toutes les predictions d'une maladie et d'une periode), pas de memoire.
- Methode inspiree de Funk et al., PLoS Comput Biol 2019 (calibration, biais, nettete, horizon) ; Bracher et al. 2021 (WIS).
- Etat : aucune fiche reelle saisie, donc aucun resultat de fiabilite ne doit etre cite.

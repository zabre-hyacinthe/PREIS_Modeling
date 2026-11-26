# Grille de relecture indépendante — PREIS-Modeling (v1, 26 nov. 2026)

Pour chaque article (titre + résumé uniquement), remplir UNE ligne. Ne pas consulter les étiquettes du tracker. Ne pas discuter avec les autres relecteurs.

| Colonne | Valeurs | Définition |
|---|---|---|
| sid | V001… | identifiant du paquet |
| is_model | Y / N / U | Recherche originale qui CONSTRUIT, CALIBRE, APPLIQUE ou ÉVALUE un modèle quantitatif (mécaniste, statistique, ML, prévision, projection, simulation, cartographie prédictive, phylodynamique, économique). N si revue, commentaire, protocole, étude purement descriptive/d'association sans modèle prédictif, essai, étude de laboratoire. U si impossible à dire sur le résumé. |
| predictive_output | forecast / projection / scenario / risk_map / prognostic / mechanistic_inference / none | Type de sortie : forecast = court terme dans le temps ; projection = à un horizon futur (ex. 2030, 2050) ; scenario = simulation d'interventions ou de what-if ; risk_map = prédiction spatiale ; prognostic = prédiction individuelle (score, nomogramme) ; mechanistic_inference = estimation de paramètres (R, taux) sans prédiction ; none. |
| infectious | Y / N / U | Maladie infectieuse (humaine ou zoonotique à impact humain). N pour cancers, maladies cardiométaboliques, santé mentale, santé animale ou végétale seule. |
| africa_setting | africa_specific / multi_incl_africa / global_incl_africa / non_africa / unclear | Où l'étude s'applique : un ou des pays africains ; plusieurs régions dont l'Afrique ; mondial avec résultats africains ; hors Afrique ; indéterminé. Un pays africain seulement cité en introduction = non_africa. |
| model_class | mechanistic_compartmental / agent_based / phylodynamic / machine_learning / time_series_forecast / spatial_risk / burden_projection / economic / simulation_scenario / statistical_prediction / none | Classe principale du modèle. |
| evidence_tier | T0 / T1 / T2 / T3 / T4 | T0 pas de modélisation ; T1 secondaire (revue, commentaire, cadre) ; T2 modèle sans validation signalée dans le résumé ; T3 validation interne (validation croisée, jeu test, calibration/ajustement aux données observées) ; T4 validation externe ou prospective, prévision confrontée aux observations, comparaison multi-modèles. |
| confidence | 1 / 2 / 3 | 1 = très incertain, 3 = sûr. |
| note | ≤ 15 mots | Raison en cas de doute. |

Règles : (1) juger le résumé tel qu'écrit, sans compléter de mémoire ; (2) en cas de doute entre deux niveaux de preuve, prendre le plus bas ; (3) U est une réponse légitime.

Sources de conception : EPIFORGE 2020 (rapport des prévisions épidémiques) ; PROBAST+AI / TRIPOD+AI 2025 (modèles de prédiction) ; Chaturvedi et al., BMC Infect Dis 2025 (revue des guides de modélisation : structure, calibration, validation, incertitude, reproductibilité) ; Bracher et al. 2021 (WIS) pour les prévisions probabilistes.

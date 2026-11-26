# Protocole de recherche PREIS-Modeling v4 (26 nov. 2026)

**Statut : protocole à valider par un second relecteur avant toute publication de chiffres.** Version machine : `config/search_protocol_v4.json` (source unique, lue par `tracker/fetch_europepmc.py`).

## Question
Quelles études de modélisation prédictive de maladies infectieuses humaines portent sur l'Afrique, avec quel degré de preuve, qui les mène, et que valent-elles une fois confrontées aux observations ?

## Cadre (JBI scoping review : Population, Concept, Contexte)
- **Population** : maladies infectieuses humaines (zoonoses à risque humain incluses).
- **Concept** : modèle quantitatif (mécaniste, statistique, apprentissage automatique, spatial, économique-décisionnel) produisant une prédiction, projection, prévision, scénario ou carte de risque.
- **Contexte** : Afrique (54 pays + continent) ; les études mondiales forment une strate séparée.

## Source et période
Europe PMC (API REST), base MEDLINE/PubMed (`SRC:MED`) : publications à comité de lecture, versions définitives. **Préprints exclus** (`SRC:PPR`). Du 2015-01-01 à la date de recherche, mise à jour hebdomadaire sur `FIRST_PDATE`.

## Requête
Trois blocs reliés par AND (modélisation, maladie, Afrique), recherche dans titre et résumé ; termes dans `config/search_protocol_v4.json`.
Dénombrement pilote du 26 nov. 2026 : 3 623 enregistrements PubMed (4 973 avec préprints, dont 1 284 préprints exclus).

## Critères
**Inclusion** : I1 publication définitive à comité de lecture 2015→ ; I2 maladie infectieuse humaine ; I3 cadre africain ; I4 modèle produisant une prédiction/projection/scénario/carte de risque ; I5 résumé en anglais, français ou portugais.
**Exclusion (cascade, un seul motif par enregistrement)** : E2 rétractée ; E7 revue ou revue systématique (gardée à part, tier T1) ; E6 commentaire, éditorial, lettre, actualité ; E9 résumé absent ; E4 sans cadre africain ; E3 maladie non infectieuse ; E5 pas de modèle prédictif détecté. E1 (préprint) est appliqué dans la requête ; E8 (doublon) au tri.

## Résultat du tri (règles, non validé humain)
3 623 identifiés → 5 doublons → 3 618 examinés → 3 rétractées, 235 revues, 38 commentaires, 6 sans résumé, 181 sans cadre africain, 55 non infectieux, 518 sans modèle prédictif → **909 à confirmer par un humain** et **1 673 inclus par les règles**. Le flux est recalculé à chaque exécution : `data/derived/prisma_flow.csv` ; décision par article : `results/screening_decisions.csv`.

## Limites connues
1. Une seule base : Embase, Scopus, Web of Science non interrogées ; recherche manuelle des références et littérature grise (OMS, Africa CDC, ECDC, hubs de prévision) à faire.
2. Recherche par titre/résumé : manque possible des modèles non cités dans le résumé.
3. Degré de preuve (T0–T4) lu sur le résumé seulement.
4. Pays : faux positifs possibles (Guinea-pig, Papua New Guinea) ; liste de pays à compléter (Comores, Cabo Verde, Congo-Brazzaville, Guinée équatoriale, Guinée-Bissau, Maurice, Sao Tomé-et-Principe, Seychelles, Soudan du Sud, RCA).
5. Leadership africain = affiliation du premier ou dernier auteur : descriptif, ne mesure pas la qualité des partenariats. Noms d'auteurs à initiales : homonymes possibles.
6. Aucune précision ou rappel n'est publiable avant l'audit humain : `pack/AUDIT_EXPRESS_30_v4.csv` (30 articles tirés au sort, 10 par tier) puis le panel ≥ 200 articles (kappa ≥ 0,6).

## Outil de prédiction et de vérification
Grille « preuve × vérification » (carte des preuves, d'après les Evidence and Gap Maps) : lignes = maladies ; colonnes = degré de preuve T0–T4 ; trois panneaux = prédictions à échéance future (à vérifier plus tard), échéance atteinte (à vérifier maintenant), sans échéance. Chaque prédiction vérifiée (module `backtest.py`) passe de « à vérifier » à un verdict (confirmée / partiellement / infirmée).

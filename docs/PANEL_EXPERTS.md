# Panel de triangulation humain — PREIS-Modeling

Objectif : un étalon-or humain avant toute publication ou chiffre cité. Les trois relecteurs IA (R1 modélisateur, R2 évaluateur de preuves, R3 praticien Africa CDC) servent de pré-tri et de mesure d'accord ; leurs erreurs sont corrélées (mêmes biais de modèle) : ils ne remplacent PAS les humains.

## Composition proposée (à recruter par le Dr Zabré)
| Rôle | Profil | Nombre |
|---|---|---|
| H1, H2 : relecteurs modélisateurs | doctorants/postdocs ou chercheurs en modélisation des maladies infectieuses (idéalement 1 basé en Afrique, 1 hors Afrique : triangulation des perspectives) | 2 |
| H3 : relecteur épidémiologiste de terrain | épidémiologiste Africa CDC / INSP / centre d'opérations d'urgence | 1 |
| A : arbitre senior | professeur/modélisateur senior (le nouveau professeur) : tranche les désaccords, valide la grille | 1 |
Charge : 200 articles × 8–10 min ≈ 30 h par relecteur (répartir sur 2 semaines) ; arbitre : désaccords seulement (~40–60 articles).

## Protocole
1. Chaque relecteur reçoit `pack/validation_pack_blind.csv` et la grille `docs/RUBRIC_TRIANGULATION.md` ; il renomme son fichier `reviewer_H1.csv` etc. (mêmes colonnes que la grille) et ne voit ni les étiquettes du tracker ni celles des autres.
2. Séance d'étalonnage de 30 min sur 10 articles (hors paquet) avant de commencer.
3. `python tests/agreement.py pack/labels` calcule le kappa de Fleiss par champ ; objectif ≥ 0,6 (accord substantiel) ; en dessous, reformuler la grille.
4. L'arbitre tranche les articles sans majorité ; le consensus humain devient l'étalon.
5. Précision/rappel du tracker estimés par strate pondérée avec intervalle de confiance (bootstrap) ; les règles ne sont réglées que sur une moitié du paquet, l'autre moitié reste pour le test final.
6. Revalidation à chaque changement majeur de règles et une fois par an ; tout chiffre publié cite la version des règles et la date du paquet.

## Reporting
Citer la grille, le nombre de relecteurs, le kappa, la précision/le rappel avec IC, et les limites (résumés seulement, une base bibliographique).

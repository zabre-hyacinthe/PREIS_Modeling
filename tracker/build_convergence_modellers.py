"""Prototypes PREIS-Modeling : (1) convergence de COUVERTURE par maladie x pays, (2) carte des modelisateurs.
HONNETETE : sans valeurs de prediction extraites, on mesure si PLUSIEURS GROUPES INDEPENDANTS ont modelise le meme sujet,
pas s'ils predisent la meme chose. Groupe = dernier auteur (proxy de l'equipe senior) ; a affiner (ORCID/affiliations).
Expertise = deduite des publications du registre (maladies, classes de modeles), pas declaree par la personne.
Sorties : data/derived/convergence_coverage.csv, modeller_map.csv (donnees publiques de publications uniquement)."""
import csv, collections, os, json
REG = "hub_export/modeling_register.csv"
OUT = "data/derived"; os.makedirs(OUT, exist_ok=True)
rows = [r for r in csv.DictReader(open(REG, encoding="utf-8-sig")) if str(r["review_status"]).startswith("retenu")]
def split(x): return [s.strip() for s in (x or "").split(";") if s.strip()]
def tier(r):
    try: return int(str(r["evidence_tier"]).replace("T", ""))
    except ValueError: return 0
g = collections.defaultdict(list)
for r in rows:
    for c in (split(r["countries_name"]) or ["Afrique (non précisé)"]):
        g[(r["pathogen_v2"] or "Non précisé", c)].append(r)
conv = []
for (p, c), rs in g.items():
    n_t3 = sum(1 for r in rs if tier(r) >= 3)
    has_auth = any((r["last_author"] or r["first_author"]).strip() for r in rs)
    if has_auth:
        ng = len({(r["last_author"] or r["first_author"] or r["doi"]).strip().lower() for r in rs})
        ngs = str(ng)
        st = "couverture solide" if (ng >= 3 and n_t3 >= 2) else ("couverture partielle" if ng >= 2 else "isolé")
    else:                                   # snapshot sans auteurs : on compte les etudes, pas les groupes
        ngs = "non évaluable (auteurs non collectés)"
        st = "plusieurs études" if len(rs) >= 3 else ("2 études" if len(rs) == 2 else "1 étude")
    conv.append(dict(pathogene=p, pays=c, etudes=len(rs), groupes_independants_proxy=ngs, etudes_T3_ou_plus=n_t3,
                     etat_couverture=st, divergence="non évaluable (valeurs non extraites)"))
conv.sort(key=lambda d: (-d["etudes"], -d["etudes_T3_ou_plus"]))
with open(f"{OUT}/convergence_coverage.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(conv[0])); w.writeheader(); w.writerows(conv)
m = collections.defaultdict(lambda: dict(n=0, first=0, last=0, path=collections.Counter(), cls=collections.Counter(), ctry=collections.Counter(), yrs=[], africa_aff=0))
for r in rows:
    for role, name in (("first", r["first_author"]), ("last", r["last_author"])):
        name = (name or "").strip()
        if not name: continue
        d = m[name]; d["n"] += 1; d[role] += 1
        d["path"][r["pathogen_v2"] or "Non précisé"] += 1; d["cls"][r["model_class_v2"] or "?"] += 1
        for c in split(r["author_countries_africa"]): d["ctry"][c] += 1
        d["yrs"].append(r["pub_year"])
mm = []
for name, d in m.items():
    mm.append(dict(modelisateur=name, publications=d["n"], premier_auteur=d["first"], dernier_auteur=d["last"],
        domaines_maladies="; ".join(k for k, _ in d["path"].most_common(3)), methodes="; ".join(k for k, _ in d["cls"].most_common(3)),
        pays_affiliation_afrique="; ".join(k for k, _ in d["ctry"].most_common(3)) or "inconnu", annees=f"{min(d['yrs'])}-{max(d['yrs'])}" if d["yrs"] else ""))
mm.sort(key=lambda d: -d["publications"])
FN = ["modelisateur","publications","premier_auteur","dernier_auteur","domaines_maladies","methodes","pays_affiliation_afrique","annees"]
with open(f"{OUT}/modeller_map.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=FN); w.writeheader(); w.writerows(mm)
if not mm: print("CARTE DES MODELISATEURS VIDE : les auteurs ne sont collectes qu'a la premiere collecte reelle Europe PMC (fetch_europepmc.py).")
print(len(rows), "etudes retenues;", len(conv), "couples maladie x pays;", collections.Counter(d["etat_couverture"] for d in conv), ";", len(mm), "modelisateurs (1er/dernier auteur)")
print(conv[:5]); print(mm[:3])

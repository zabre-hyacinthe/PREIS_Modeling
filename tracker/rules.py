# -*- coding: utf-8 -*-
"""PREIS Model Tracker v2 - regles explicites et auditables (aucun modele opaque).
Chaque decision garde les termes qui l'ont declenchee (colonnes *_terms) pour relecture par un epidemiologiste."""
import re, html

def clean(s):
    s = html.unescape(str(s)) if s == s and s is not None else ""
    return re.sub(r"\s+", " ", s).strip()

def norm_title(s):
    return re.sub(r"[^a-z0-9]+", " ", clean(s).lower()).strip()

# ---------- Geographie (sensible a la casse pour les noms propres) ----------
_C = {  # iso3: (nom, regex)
 "DZA": ("Algeria", r"Algeria|Algerian"), "AGO": ("Angola", r"Angola|Angolan"), "BEN": ("Benin", r"Benin|Beninese"),
 "BWA": ("Botswana", r"Botswana"), "BFA": ("Burkina Faso", r"Burkina Faso|Burkinab[eè]"), "BDI": ("Burundi", r"Burundi"),
 "CPV": ("Cabo Verde", r"Cabo Verde|Cape Verde"), "CMR": ("Cameroon", r"Cameroon|Cameroun"),
 "CAF": ("Central African Republic", r"Central African Republic"), "TCD": ("Chad", r"Chad(?!\w)|Chadian"),
 "COM": ("Comoros", r"Comoros"), "COG": ("Republic of the Congo", r"Republic of (the )?Congo|Congo[- ]Brazzaville"),
 "COD": ("DR Congo", r"Democratic Republic of (the )?Congo|DR Congo|D\.R\. Congo|DRC(?!\w)|Congo[- ]Kinshasa"),
 "CIV": ("Côte d'Ivoire", r"C[ôo]te d.Ivoire|Ivory Coast|Ivorian"), "DJI": ("Djibouti", r"Djibouti"), "EGY": ("Egypt", r"Egypt|Egyptian"),
 "GNQ": ("Equatorial Guinea", r"Equatorial Guinea"), "ERI": ("Eritrea", r"Eritrea"), "SWZ": ("Eswatini", r"Eswatini|Swaziland"),
 "ETH": ("Ethiopia", r"Ethiopia"), "GAB": ("Gabon", r"Gabon"), "GMB": ("Gambia", r"Gambia"), "GHA": ("Ghana", r"Ghana"),
 "GIN": ("Guinea", r"(?<!Papua New )(?<!Equatorial )Guinea(?![- ]Bissau)(?! pig)|Guinean"), "GNB": ("Guinea-Bissau", r"Guinea[- ]Bissau"),
 "KEN": ("Kenya", r"Kenya"), "LSO": ("Lesotho", r"Lesotho"), "LBR": ("Liberia", r"Liberia"), "LBY": ("Libya", r"Libya"),
 "MDG": ("Madagascar", r"Madagascar|Malagasy"), "MWI": ("Malawi", r"Malawi"), "MLI": ("Mali", r"Mali(?!\w)|Malian"),
 "MRT": ("Mauritania", r"Mauritania"), "MUS": ("Mauritius", r"Mauritius"), "MAR": ("Morocco", r"Morocc"),
 "MOZ": ("Mozambique", r"Mozambi"), "NAM": ("Namibia", r"Namibia"), "NER": ("Niger", r"Niger(?!ia)(?!\w)|Nigerien"),
 "NGA": ("Nigeria", r"Nigeria"), "RWA": ("Rwanda", r"Rwanda"), "STP": ("São Tomé and Príncipe", r"S[ãa]o Tom[ée]"),
 "SEN": ("Senegal", r"Senegal"), "SYC": ("Seychelles", r"Seychelles"), "SLE": ("Sierra Leone", r"Sierra Leone"),
 "SOM": ("Somalia", r"Somalia"), "ZAF": ("South Africa", r"South Africa"), "SSD": ("South Sudan", r"South Sudan"),
 "SDN": ("Sudan", r"(?<!South )Sudan"), "TZA": ("Tanzania", r"Tanzania"), "TGO": ("Togo", r"Togo(?!\w)|Togolese"),
 "TUN": ("Tunisia", r"Tunisia"), "UGA": ("Uganda", r"Uganda"), "ZMB": ("Zambia", r"Zambia"), "ZWE": ("Zimbabwe", r"Zimbabwe"),
}
COUNTRY_RE = {k: re.compile(r"(?<![A-Za-z])(?:%s)" % v[1]) for k, v in _C.items()}
COUNTRY_NAME = {k: v[0] for k, v in _C.items()}
REGION_RE = re.compile(r"(?<![A-Za-z])(sub-?Saharan Africa|SSA(?!\w)|Africa(?!n[- ]American)|African(?![- ]American)(?! ancestry)|Sahel|Horn of Africa|Maghreb)", re.I)
GLOBAL_TITLE_RE = re.compile(r"\bglobal(ly)?\b|worldwide|\bGBD\b|Global Burden of Disease|\bworld\b", re.I)
GLOBAL_ABS_RE = re.compile(r"Global Burden of Disease|\bGBD\b|\b(1[89]\d|2\d\d) countries\b|worldwide|all (world )?regions", re.I)

NONAFR_TITLE_RE = re.compile(r"\b(Asia|Asian|Europe|European|China|Chinese|India|Indian|Haiti|Brazil|Brazilian|Mexico|Yucat[aá]n|United States|USA|U\.S\.|Japan|Korea|Thailand|Vietnam|Bangladesh|Pakistan|Nepal|Peru|Colombia|Iran|Saudi|Australia|Canada|England|UK)\b")
def geo(title, abstract):
    t, a = clean(title), clean(abstract)
    in_title = [k for k, r in COUNTRY_RE.items() if r.search(t)]
    in_abs = [k for k, r in COUNTRY_RE.items() if r.search(a)]
    countries = sorted(set(in_title) | set(in_abs))
    reg_t = bool(REGION_RE.search(t))
    n_abs = len(re.findall(REGION_RE, a)) + sum(len(COUNTRY_RE[k].findall(a)) for k in in_abs)
    glob = bool(GLOBAL_TITLE_RE.search(t) or GLOBAL_ABS_RE.search(a))
    if (in_title or reg_t):
        rel = "Afrique"
    elif NONAFR_TITLE_RE.search(t):
        rel = "Hors Afrique / non précisé"
    elif n_abs >= 2 and not glob:
        rel = "Afrique"
    elif n_abs >= 1:
        rel = "Mondial (Afrique mentionnée)" if glob else "Afrique (cadre à confirmer)"
    else:
        rel = "Hors Afrique / non précisé"
    if rel.startswith("Afrique"):
        scope = "national" if len(countries) == 1 else ("multi-pays" if len(countries) >= 2 else "régional/continental")
    elif rel.startswith("Mondial"):
        scope = "mondial"
    else:
        scope = "non précisé"
    return dict(africa_relevance=rel, geo_scope_v2=scope, countries_iso3="|".join(countries),
                countries_name="; ".join(COUNTRY_NAME[c] for c in countries), n_countries=len(countries))

# ---------- Classes de modeles (premier niveau qui correspond ; tous les termes sont conserves) ----------
M = [
 ("Phylodynamique / génomique", r"phylodynamic|phylogeograph|molecular clock"),
 ("Agent / individu-centré", r"agent[- ]based|individual[- ]based|microsimulation"),
 ("Compartimental / mécaniste", r"\b(sir|seir|seirs|sis|seiar|seird|seiqr)\b|compartmental|mathematical model|transmission (dynamic|model)|dynamic(al)? transmission|ordinary differential|reaction[- ]diffusion|metapopulation|stochastic (epidemic )?model|next[- ]generation matrix|fractional[- ]order"),
 ("Apprentissage automatique / IA", r"machine learning|random forest|xgboost|gradient boost|lightgbm|catboost|neural network|deep learning|\blstm\b|support vector|large language model|\bllms?\b|k-nearest|naive bayes"),
 ("Séries temporelles / prévision", r"\barima\b|sarima|forecast|nowcast|prophet model|exponential smoothing|(epidemic|outbreak) early warning|early warning system"),
 ("Spatial / cartographie du risque", r"geostatistic|species distribution|ecological niche|maxent|risk map|(environmental|climat\w+) suitability|model-based geostatistic|kriging|\binla\b|bayesian spatial|spatial (prediction|model+ing)"),
 ("Projection de charge / tendances", r"age[- ]period[- ]cohort|\bapc model|projections? (to|until|through|by) (the year )?(20|21)\d\d|projected (burden|incidence|prevalence|mortality|cases|deaths)|forecast(ed)? (to|until|through|by) (20|21)\d\d|predictions? by"),
 ("Économique / décisionnel", r"cost[- ]effectiveness|budget impact|markov|decision[- ]analytic|return on investment"),
 ("Simulation / scénarios", r"simulation (model|study)|we simulat|were simulated|simulated (the )?(impact|effect|outbreak|scenario)|modell?ing study|modell?ed (impact|effect)|what-if|counterfactual|scenario (analysis|modell?ing)|projected impact"),
 ("Régression / prédiction statistique", r"prediction model|prognostic model|predictive model|risk score|nomogram"),
]
M_RE = [(n, re.compile(p, re.I)) for n, p in M]
STRONG = {n for n, _ in M} - {"Régression / prédiction statistique"}
DESIGN_EXCL = re.compile(r"systematic review|scoping review|meta-?analysis|narrative review|literature review|umbrella review|\bprotocol\b|cross-sectional|case-control|case series|randomi[sz]ed|clinical trial|qualitative|interviews?\b|household survey|\bin mice\b|\bin vitro\b|mouse model|murine|ex vivo|interrupted time series|position statement|\bcomprehensive review\b|a review\b", re.I)

SPEC_RE = re.compile(r"projections? (to|until|through|by)|projected|age-period-cohort|markov|ecological niche|species distribution|maxent|predictive model|prediction model|prognostic model|mathematical model|transmission model|compartmental|agent-based|individual-based|\\b(seir|seird|sir)\\b|geostatistic|\\bsarima\\b|\\barima\\b|xgboost|random forest|risk map|nowcast", re.I)

def model_class(title, abstract, keywords=""):
    t = clean(title); ab = clean(abstract); full = clean(" ".join([t, ab, clean(keywords)]))
    design = DESIGN_EXCL.search(t) or DESIGN_EXCL.search(ab[:300])
    hits = {}
    for n, r in M_RE:
        f = sorted({m.group(0).lower() for m in r.finditer(full)})
        if f: hits[n] = f
    if not hits:
        return dict(model_class_v2="Non classé", method_terms="", modelling_confidence="aucune", design_excluded=bool(design))
    RC = dict(M_RE)
    score = {n: 5 * bool(RC[n].search(t)) * 3 + len(RC[n].findall(full)) for n in hits}
    cls = max(score, key=lambda n: (score[n], -[x for x, _ in M_RE].index(n)))
    in_title = bool(RC[cls].search(t))
    rcls = RC[cls]
    n_terms = len(rcls.findall(full))   # occurrences (pas seulement termes distincts)
    if re.search(r"\breview\b|commentary|perspective|viewpoint|lessons|capacity|strategy|knowledge|training|virology|pathogenesis", t, re.I) and not in_title:
        design = True
    if design and not in_title:
        conf = "faible"
    elif in_title:
        conf = "élevée"
    elif cls in STRONG and (n_terms >= 3 or any(SPEC_RE.search(x) for x in hits[cls])):
        conf = "moyenne"   # termes spécifiques de modélisation : une occurrence suffit
    else:
        conf = "faible"
    return dict(model_class_v2=cls, method_terms="|".join(hits[cls][:6]), modelling_confidence=conf, design_excluded=bool(design))

# ---------- Pathogenes / themes (aucune valeur par defaut) ----------
P = [
 ("Ebola / filovirus", r"ebola|bundibugyo|marburg|filovir"), ("Lassa", r"\blassa"), ("Mpox", r"mpox|monkeypox"),
 ("Choléra", r"cholera|vibrio cholerae"), ("Rougeole", r"measles|rubeola"), ("Polio", r"polio(?!m)|poliovirus|cvdpv|acute flaccid"),
 ("Fièvre jaune", r"yellow fever"), ("Dengue", r"dengue"), ("Chikungunya", r"chikungunya"), ("Zika", r"\bzika"),
 ("Fièvre de la vallée du Rift", r"rift valley"), ("Fièvre CCHF", r"crimean[- ]congo|cchf"), ("Rage", r"\brabies"),
 ("Anthrax", r"anthrax"), ("Peste", r"\bplague\b|yersinia pestis"), ("Méningite", r"meningococc|meningitis|neisseria"),
 ("Typhoïde", r"typhoid|salmonella typhi"), ("Diphtérie", r"diphtheria"), ("Coqueluche", r"pertussis|whooping"),
 ("Paludisme", r"malaria|plasmodium|anopheles"), ("Tuberculose", r"tubercul|\btb\b|mycobacterium"), ("VIH/sida", r"\bhiv\b|\baids\b"),
 ("Hépatites", r"hepatitis"), ("COVID-19", r"covid|sars-cov-2|coronavirus"), ("Grippe", r"influenza|\bflu\b|h5n1|h1n1|h3n2|h7n9"),
 ("VRS", r"respiratory syncytial|\brsv\b"), ("HPV", r"papillomavirus|\bhpv\b"), ("Schistosomiase", r"schistosom|bilharz"),
 ("Onchocercose", r"onchocerc"), ("Filariose lymphatique", r"lymphatic filariasis"), ("Trachome", r"trachoma"),
 ("Leishmaniose", r"leishmani"), ("Trypanosomiase", r"trypanosom|sleeping sickness"), ("Helminthiases", r"helminth|hookworm|ascaris"),
 ("Résistance antimicrobienne", r"antimicrobial resistance|\bamr\b|antibiotic resistance"), ("Infections respiratoires", r"pneumonia|respiratory infection|\bari\b"),
]
P_RE = [(n, re.compile(p, re.I)) for n, p in P]
NCD_RE = re.compile(r"cancer|carcinoma|tumou?r|diabet|cardiovascular|stroke|hypertension|ischaemic|ischemic|depress|anxiety|asthma|\bcopd\b|obesity|\bbmi\b|injur|burn |kidney|dementia|alzheimer|osteo|gout|substance use|autis|mental (health|disorder)|sickle|epilep|alcohol|smoking|tobacco|\bbirth defect", re.I)
MCH_RE = re.compile(r"contracepti|maternal|neonatal|stunting|undernutrition|malnutrition|anaemia|anemia|breastfeeding|antenatal|fertility", re.I)
PRIORITY = {"Ebola / filovirus", "Lassa", "Mpox", "Choléra", "Rougeole", "Polio", "Fièvre jaune", "Fièvre de la vallée du Rift", "Fièvre CCHF", "Anthrax", "Peste", "Méningite", "Grippe", "Dengue", "Rage"}

GENERIC_INF = re.compile(r"epidemic|outbreak|pandemic|infectious disease|communicable|vaccin|zoono|vector-borne|transmission", re.I)
def pathogen(title, abstract):
    t, a = clean(title), clean(abstract)
    hits = []
    for n, r in P_RE:
        mt = len(r.findall(t)); ma = len(r.findall(a))
        if mt or ma: hits.append((n, mt * 5 + ma, mt, ma))
    hits.sort(key=lambda x: -x[1])
    strong = [h for h in hits if h[2] >= 1 or h[3] >= 3]
    if strong:
        prim = strong[0][0]; domain = "Maladie infectieuse"
        if NCD_RE.search(t) and strong[0][2] == 0:
            domain = "Hors périmètre (maladies non transmissibles)"
    elif GENERIC_INF.search(t) or len(GENERIC_INF.findall(a[:600])) >= 2:
        prim, domain = "Non précisé (infectieux générique)", "Maladie infectieuse"
    elif NCD_RE.search(t + " " + a[:400]):
        prim, domain = "Non précisé", "Hors périmètre (maladies non transmissibles)"
    elif MCH_RE.search(t + " " + a[:400]):
        prim, domain = "Non précisé", "Hors périmètre (santé maternelle, infantile, nutrition)"
    else:
        prim, domain = "Non précisé", "Non précisé"
    return dict(pathogen_v2=prim, pathogens_all="|".join(h[0] for h in strong[:4]), domain_v2=domain, priority_pathogen=prim in PRIORITY)

# ---------- Annee cible de la prediction ----------
YR = re.compile(r"(?:by|until|through|to|in|for|towards?|up to|horizon of)\s+(?:the\s+year\s+)?(20[2-9]\d|2100)\b|(?:projection|forecast|prediction|project(?:ed)?|predicted|scenario)s?\b[^.]{0,60}?\b(20[2-9]\d|2100)\b", re.I)
def target_year(title, abstract, pub_year):
    txt = clean(title) + ". " + clean(abstract)
    ys = [int(g) for m in YR.finditer(txt) for g in m.groups() if g]
    try: py = int(pub_year)
    except Exception: py = 2025
    ys = [y for y in ys if py <= y <= 2100]
    if not ys: return dict(target_year_v2="", horizon_years="")
    y = max(ys); return dict(target_year_v2=y, horizon_years=y - py)

# ---------- Indicateurs de qualite declares (resume uniquement ; ce n'est PAS une evaluation critique) ----------
EV = {
 "validation_mentioned": r"cross[- ]validat|out[- ]of[- ]sample|external validation|\bvalidat|back-?test|held-?out|hold-?out|train(ing)?[ /-]+(and|/)?[ -]*test|calibrat|rolling[- ]origin",
 "uncertainty_mentioned": r"credible interval|confidence interval|uncertainty interval|\b95 ?% ?(ci|cri|ui)\b|prediction interval|uncertaint",
 "code_or_data_open": r"github|code (is |are )?(publicly )?available|open[- ]source|zenodo|reproducib|data (is |are )?available",
 "real_data_mentioned": r"surveillance data|demographic and health survey|\bdhs\b|\bgbd\b|line list|routine data|dhis2|hospital records|cohort|serolog|notified cases|reported cases",
}
EV_RE = {k: re.compile(v, re.I) for k, v in EV.items()}
def evidence(title, abstract):
    full = clean(title) + " " + clean(abstract)
    f = {k: bool(r.search(full)) for k, r in EV_RE.items()}
    f["evidence_flags"] = int(f["validation_mentioned"]) + int(f["uncertainty_mentioned"]) + int(f["code_or_data_open"])
    return f


# ---------- v3 : degre de preuve (niveau abstract, PROVISOIRE) ----------
# Echelle propre au tracker, inspiree de EPIFORGE 2020 (evaluation des previsions), PROBAST/TRIPOD+AI (validation) et
# de la scoping review BMC Infect Dis 2025 (Chaturvedi et al.) : dimensions structure, calibration, validation, incertitude, reproductibilite.
EXT_VAL = re.compile(r"external(ly)? validat|prospective(ly)? (validat|evaluat|forecast)|real-time (forecast|evaluat)|retrospective(ly)? (forecast|evaluat)|independent (data ?set|cohort|data)|compared (with|to|against) (the )?(observed|reported|actual|surveillance)|against (observed|reported|actual) (data|cases|incidence)|forecast (accuracy|performance|skill|evaluation)|weighted interval score|multi-?model (comparison|ensemble)|model comparison|ensemble (forecast|model)|out-of-sample", re.I)
INT_VAL = re.compile(r"cross-?validat|validated|validation|held-?out|train(ing)?[ /-]+(and )?test|test (set|data)|back-?test|goodness[- ]of[- ]fit|calibrat|fitted to|fit(s|ted)? (the )?(observed|reported)|\bauc\b|\brmse\b|\bmape\b|mean absolute|accuracy", re.I)
UNC = re.compile(r"uncertaint|confidence interval|credible interval|prediction interval|\b95 ?%|probabilistic|sensitivity analys|bayesian|monte carlo|bootstrap", re.I)
CODE = re.compile(r"github|gitlab|zenodo|osf\.io|figshare|code (is |are )?(publicly )?available|open[- ]source|r package|python package|source code|supplementary code", re.I)
DATA = re.compile(r"data (is |are )?(publicly )?available|publicly available data|open data|data availability|dhis2|available (at|from|on) (the )?(repository|zenodo|figshare)", re.I)
ASSUME = re.compile(r"assum(e|ed|ption)|parameter(s|ised|ized)? (were|was|from)|serial interval|reproduction number|\br0\b|\brt\b|incubation period|priors?\b", re.I)
SECONDARY = re.compile(r"systematic review|scoping review|meta-?analysis|literature review|narrative review|commentary|perspective|guideline|capacity|framework for|protocol", re.I)

def evidence_tier(title, abstract, is_model):
    """T0 hors modelisation ; T1 secondaire (revue/commentaire/cadre) ; T2 modele sans validation signalee ;
    T3 validation interne/calibration ; T4 validation externe, prospective ou prevision confrontee aux observations / comparaison multi-modeles."""
    t, a = clean(title), clean(abstract); full = t + " " + a
    f = dict(ev_ext_validation=bool(EXT_VAL.search(full)), ev_int_validation=bool(INT_VAL.search(full)), ev_uncertainty=bool(UNC.search(full)),
             ev_code_open=bool(CODE.search(full)), ev_data_open=bool(DATA.search(full)), ev_assumptions=bool(ASSUME.search(full)))
    f["transparency_score"] = int(f["ev_ext_validation"] or f["ev_int_validation"]) + int(f["ev_uncertainty"]) + int(f["ev_code_open"]) + int(f["ev_data_open"]) + int(f["ev_assumptions"])
    if not is_model:
        f["evidence_tier"] = "T1" if SECONDARY.search(t) else "T0"
    elif f["ev_ext_validation"]: f["evidence_tier"] = "T4"
    elif f["ev_int_validation"]: f["evidence_tier"] = "T3"
    else: f["evidence_tier"] = "T2"
    f["evidence_basis"] = "résumé uniquement (provisoire)"
    return f

# ---------- v3 : qui / ou (auteurs, affiliations) ----------
def author_info(authors, affils_by_author):
    """authors: liste de noms ; affils_by_author: liste de textes d'affiliation (un par auteur, '' si absent)."""
    out = dict(first_author=authors[0] if authors else "", last_author=authors[-1] if authors else "", n_authors=len(authors))
    def ctry(txt):
        return sorted({k for k, r in COUNTRY_RE.items() if r.search(txt or "")})
    af = [ctry(x) for x in affils_by_author]
    out["author_countries_africa"] = "|".join(sorted({c for l in af for c in l}))
    out["n_authors_with_affiliation"] = sum(1 for x in affils_by_author if x)
    fa = bool(af and af[0]); la = bool(af and af[-1]); anya = any(af)
    out["africa_first_author"] = fa; out["africa_last_author"] = la; out["africa_any_author"] = anya
    out["africa_led"] = fa or la
    # indicateur descriptif d'equite : etude centree Afrique SANS aucun auteur affilie en Afrique (parmi ceux avec affiliations connues)
    out["no_african_affiliation"] = (not anya) and out["n_authors_with_affiliation"] > 0
    return out

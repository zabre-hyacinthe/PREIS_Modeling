"""PREIS Modeling - validation historique (backtest) et suivi de realisation.

Compare une fiche de prediction a ce qui s'est passe. Aucune valeur n'est inventee :
une fiche sans resultat observe sourcé reste 'en attente'. Seuils = propositions de
travail, a valider par le panel (docs/PANEL_EXPERTS.md).
Metriques inspirees de : Funk et al. PLoS Comput Biol 2019 (calibration, biais, nettete,
comparaison a un modele nul, effet de l'horizon) ; Bracher et al. 2021 (WIS) ;
Cramer et al. PNAS 2022 (comparaison aux ensembles/references).
"""
import csv, math, sys, json
from datetime import date
from collections import defaultdict

TH_CONF = (2/3, 1.5)   # ratio observe/predit : confirmee
TH_PART = (0.5, 2.0)   # partiellement confirmee
FIELDS = ["record_id","doi","pathogen","country","target","kind","prediction_date",
          "data_cutoff_date","target_start","target_end","point","lo","hi","interval_level",
          "prob","scenario_conditional","assumptions_held","model_class","group_id",
          "null_forecast","observed","observed_source","observed_known_date","notes"]
KINDS = {"point","interval","binary","quantiles"}

def _f(x):
    try:
        if x is None or str(x).strip()=="" : return None
        return float(x)
    except ValueError:
        return None

def _d(x):
    try: return date.fromisoformat(str(x).strip()[:10])
    except ValueError: return None

def wis_interval(lo, hi, y, level=0.95):
    """Interval score pour un intervalle central (Gneiting-Raftery / Bracher 2021)."""
    a = 1 - level
    return (hi - lo) + (2/a)*max(lo-y, 0) + (2/a)*max(y-hi, 0)

def score_record(r):
    """Retourne dict: status, verdict, ratio, log_ratio, covered, interval_score, brier, skill_vs_null, horizon_days, flags."""
    out = {"status":"en attente","verdict":"","ratio":None,"log_ratio":None,"covered":None,
           "interval_score":None,"brier":None,"skill_vs_null":None,"horizon_days":None,"flags":[]}
    pd_, ts, te = _d(r.get("prediction_date")), _d(r.get("target_start")), _d(r.get("target_end"))
    dc = _d(r.get("data_cutoff_date"))
    ref = dc or pd_
    if ref is None or ts is None:
        out["status"]="non evaluable"; out["verdict"]="dates manquantes"; return out
    if ref >= ts and (te is None or ref >= te):
        out["status"]="invalide"; out["verdict"]="prediction posterieure a la periode cible (hindsight)"; return out
    if ref >= ts: out["flags"].append("periode cible deja commencee a la date de prediction")
    out["horizon_days"] = (ts - ref).days
    obs = _f(r.get("observed"))
    if obs is None:
        return out
    if not str(r.get("observed_source","")).strip():
        out["status"]="non evaluable"; out["verdict"]="resultat sans source"; return out
    cond = str(r.get("scenario_conditional","")).strip().upper() in ("Y","1","TRUE","OUI")
    held = str(r.get("assumptions_held","")).strip().upper()
    if cond and held != "Y":
        out["status"]="non evaluable" if held=="N" else "en attente"
        out["verdict"]="scenario: hypotheses non realisees" if held=="N" else "scenario: verifier d'abord les hypotheses"
        return out
    kind = r.get("kind","point")
    pt, lo, hi, p = _f(r.get("point")), _f(r.get("lo")), _f(r.get("hi")), _f(r.get("prob"))
    out["status"]="evalue"
    if kind=="binary":
        if p is None: out["status"]="non evaluable"; out["verdict"]="probabilite manquante"; return out
        y = 1.0 if obs >= 0.5 else 0.0
        out["brier"] = (p - y)**2
        out["verdict"] = "confirmee" if (p>=0.5)==(y==1.0) else "infirmee"
        return out
    if pt is None and lo is not None and hi is not None: pt = (lo+hi)/2
    if pt is None or pt <= 0 or obs < 0:
        out["status"]="non evaluable"; out["verdict"]="valeur predite absente ou nulle"; return out
    ratio = (obs/pt) if pt else None
    out["ratio"] = ratio
    if ratio and ratio>0: out["log_ratio"] = math.log(ratio)
    if lo is not None and hi is not None:
        out["covered"] = lo <= obs <= hi
        out["interval_score"] = wis_interval(lo, hi, obs, _f(r.get("interval_level")) or 0.95)
        if out["covered"]: out["verdict"]="confirmee"
    if not out["verdict"]:
        if ratio and TH_CONF[0] <= ratio <= TH_CONF[1]: out["verdict"]="confirmee"
        elif ratio and TH_PART[0] <= ratio <= TH_PART[1]: out["verdict"]="partiellement confirmee"
        else: out["verdict"]="infirmee"
    nul = _f(r.get("null_forecast"))
    if nul is not None:
        e_m, e_n = abs(obs-pt), abs(obs-nul)
        out["skill_vs_null"] = (1 - e_m/e_n) if e_n > 0 else None
    return out

def read(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def summarize(rows, key):
    g = defaultdict(list)
    for r in rows: g[r.get(key) or "inconnu"].append(r)
    res = []
    for k, rs in sorted(g.items()):
        ev = [x for x in rs if x["_s"]["status"]=="evalue"]
        n = len(ev)
        conf = sum(1 for x in ev if x["_s"]["verdict"]=="confirmee")
        lr = sorted(x["_s"]["log_ratio"] for x in ev if x["_s"]["log_ratio"] is not None)
        med = lr[len(lr)//2] if lr else None
        cov = [x["_s"]["covered"] for x in ev if x["_s"]["covered"] is not None]
        res.append({key:k,"fiches":len(rs),"evaluees":n,
            "part_confirmee": round(conf/n,2) if n else None,
            "biais_median_log_ratio": round(med,2) if med is not None else None,
            "couverture_intervalle": round(sum(cov)/len(cov),2) if cov else None})
    return res

def run(path, out_dir):
    rows = read(path)
    for r in rows: r["_s"] = score_record(r)
    import os
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir,"backtest_scored.csv"),"w",encoding="utf-8",newline="") as f:
        cols = FIELDS+["status","verdict","ratio","covered","interval_score","brier","skill_vs_null","horizon_days","flags"]
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore"); w.writeheader()
        for r in rows:
            d = {k: r.get(k,"") for k in FIELDS}; d.update({k: r["_s"][k] for k in cols if k in r["_s"]})
            d["flags"] = "; ".join(r["_s"]["flags"]); w.writerow(d)
    rep = {"n":len(rows),"statuts":{s:sum(1 for r in rows if r["_s"]["status"]==s) for s in {r["_s"]["status"] for r in rows}},
           "par_pathogene":summarize(rows,"pathogen"),"par_classe":summarize(rows,"model_class"),
           "avertissement":"Seuils = propositions; echantillon de fiches choisies = biais de selection possible (on retient les cas celebres). Ne jamais citer sans panel."}
    with open(os.path.join(out_dir,"backtest_report.json"),"w",encoding="utf-8") as f: json.dump(rep,f,ensure_ascii=False,indent=1)
    return rep

if __name__ == "__main__":
    p = sys.argv[1] if len(sys.argv)>1 else "config/prediction_records.csv"
    print(json.dumps(run(p, sys.argv[2] if len(sys.argv)>2 else "data/backtest"), ensure_ascii=False, indent=1))

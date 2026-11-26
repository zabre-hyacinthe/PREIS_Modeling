#!/usr/bin/env python3
"""PREIS-Modeling : collecte Europe PMC (API REST publique, resultType=core) -> qui / ou / quand / type de publication.
A LANCER SUR WINDOWS (la VM de travail n'atteint pas Europe PMC). Aucun paquet a installer (bibliotheque standard).
Usage : python fetch_europepmc.py --start 2015-01-01 [--since 2026-05-01] [--max 20000]
Sorties : results/raw/epmc_core_<date>.jsonl (brut, ajout) et results/articles_v3_raw.csv (normalise, dedoublonne par id).
Incremental : --since reprend depuis une date de premiere publication (FIRST_PDATE) ; le brut est conserve pour audit.
Inclut les PREPRINTS (SRC:PPR), exclus par V10, pour suivre la modelisation en temps reel ; ils sont marques is_preprint."""
import argparse, csv, datetime as dt, json, os, sys, time, urllib.parse, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rules as R

BASE = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
MODEL_TERMS = ['"mathematical model"', '"mathematical modelling"', '"mathematical modeling"', '"transmission model"', '"transmission dynamics"', 'compartmental', 'SEIR', 'SIR', '"agent-based"', '"individual-based"',
    'forecast', 'forecasting', 'nowcast', 'projection', 'projections', 'simulation', '"machine learning"', '"deep learning"', '"random forest"', 'ARIMA', '"time series"', '"risk map"', '"species distribution"', 'geostatistical',
    '"early warning"', 'phylodynamic', '"scenario analysis"', '"modelling study"', '"modeling study"', '"prediction model"', '"predictive model"', '"cost-effectiveness"', '"reproduction number"', 'Bayesian']
INFECT = ['infectious', 'epidemic', 'outbreak', 'pandemic', 'malaria', 'tuberculosis', 'HIV', 'cholera', 'Ebola', 'mpox', 'monkeypox', 'COVID-19', 'measles', 'polio', 'dengue', 'Lassa', 'meningitis', '"yellow fever"', 'influenza', 'typhoid', '"Rift Valley"', 'schistosomiasis', 'vaccin*', 'zoono*', 'hepatitis', 'rabies', 'anthrax', 'plague', 'Marburg', 'chikungunya']

def africa_block(chunk):
    return "(" + " OR ".join('"%s"' % n for n in chunk) + ")"

def build_queries(start, since, sources=True):
    """Requete unique issue du protocole v4 (config/search_protocol_v4.json) : modelisation ET maladie ET Afrique, publications definitives PubMed (SRC:MED), sans preprints."""
    pr = json.load(open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "search_protocol_v4.json"), encoding="utf-8"))
    q = lambda ks: "(" + " OR ".join('TITLE_ABS:"%s"' % k if (" " in k or "-" in k) else "TITLE_ABS:%s" % k for k in ks) + ")"
    date = "FIRST_PDATE:[%s TO %s]" % (since or start or pr["date_from"], dt.date.today().isoformat())
    return [" AND ".join(q(pr["blocks"][b]) for b in ("modeling", "disease", "africa")) + " AND " + date + " AND SRC:MED"]

def get(url, tries=5):
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "PREIS-Modeling/3.0 (Africa CDC; contact: hub)"})
            with urllib.request.urlopen(req, timeout=60) as r: return json.loads(r.read().decode("utf-8"))
        except Exception as e:
            wait = 2 ** k; print("  retry", k + 1, e, "attente", wait, "s", file=sys.stderr); time.sleep(wait)
    raise RuntimeError("echec reseau apres %d essais : %s" % (tries, url))

def _j(sep, xs):
    """Joint seulement des chaines (Europe PMC renvoie parfois null dans les listes)."""
    return sep.join(str(x) for x in (xs or []) if x is not None and str(x) != "")

def parse_record(rec):
    """Normalise un enregistrement 'core' de Europe PMC. Tolerant aux champs absents."""
    al = (rec.get("authorList") or {}).get("author") or []
    names, affs = [], []
    for a in al:
        names.append(a.get("fullName") or ((a.get("firstName") or "") + " " + (a.get("lastName") or "")).strip())
        det = ((a.get("authorAffiliationDetailsList") or {}).get("authorAffiliation")) or []
        affs.append(" ; ".join((d.get("affiliation") or "") for d in det if isinstance(d, dict)) or (a.get("affiliation") or ""))
    if not names and rec.get("authorString"):
        names = [x.strip() for x in rec["authorString"].rstrip(".").split(",") if x.strip()]; affs = [""] * len(names)
    pt = [x for x in ((rec.get("pubTypeList") or {}).get("pubType") or []) if x]
    fl = (rec.get("fullTextUrlList") or {}).get("fullTextUrl") or []
    d = dict(epmc_id=rec.get("id", ""), source=rec.get("source", ""), pmid=rec.get("pmid", ""), pmcid=rec.get("pmcid", ""), doi=rec.get("doi", ""),
             title=R.clean(rec.get("title") or ""), abstract=R.clean(rec.get("abstractText") or ""), journal=((rec.get("journalInfo") or {}).get("journal") or {}).get("title", ""),
             first_pub_date=rec.get("firstPublicationDate", ""), pub_year=rec.get("pubYear", ""), cited_by=rec.get("citedByCount", 0), is_open_access=rec.get("isOpenAccess", ""),
             pub_types=_j("|", pt), is_preprint=(rec.get("source") == "PPR") or ("Preprint" in pt),
             is_retracted=("Retracted Publication" in pt) or ("retraction" in R.clean(rec.get("title") or "").lower()[:40]),
             grants="|".join(sorted({(g.get("agency") or "") for g in ((rec.get("grantsList") or {}).get("grant") or []) if g.get("agency")})),
             keywords=_j("|", (rec.get("keywordList") or {}).get("keyword")), has_fulltext_oa=any(f.get("availability") == "Open access" for f in fl),
             url=("https://doi.org/" + rec["doi"]) if rec.get("doi") else ("https://europepmc.org/article/%s/%s" % (rec.get("source", ""), rec.get("id", ""))),
             authors="; ".join(names))
    d.update(R.author_info(names, affs)); return d

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--start", default="2015-01-01"); ap.add_argument("--since", default=None); ap.add_argument("--max", type=int, default=50000); ap.add_argument("--page", type=int, default=500)
    a = ap.parse_args(); root = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); raw = os.path.join(root, "results", "raw"); os.makedirs(raw, exist_ok=True)
    stamp = dt.datetime.utcnow().strftime("%Y%m%d_%H%M%S"); jf = open(os.path.join(raw, "epmc_core_%s.jsonl" % stamp), "w", encoding="utf-8")
    seen, rows = {}, []
    outcsv = os.path.join(root, "results", "articles_v3_raw.csv")
    if os.path.exists(outcsv):   # incremental : on garde l'existant
        import pandas as pd
        for r in pd.read_csv(outcsv, dtype=str, keep_default_na=False).to_dict("records"): seen[(r["source"], r["epmc_id"])] = r
    n_new = 0; n_err = 0
    for qi, q in enumerate(build_queries(a.start, a.since)):
        cursor = "*"
        while True:
            url = BASE + "?" + urllib.parse.urlencode(dict(query=q, resultType="core", pageSize=a.page, cursorMark=cursor, format="json"))
            j = get(url); res = (j.get("resultList") or {}).get("result") or []
            for rec in res:
                jf.write(json.dumps(rec, ensure_ascii=False) + "\n")
                try: d = parse_record(rec)
                except Exception as e:
                    n_err += 1; print("  notice ignoree (%s) : %s/%s" % (type(e).__name__, rec.get("source"), rec.get("id")), file=sys.stderr); continue
                k = (d["source"], d["epmc_id"])
                if k not in seen: n_new += 1
                seen[k] = d
            nxt = j.get("nextCursorMark")
            print("requete %d : %d recus, total unique %d" % (qi + 1, len(res), len(seen)), flush=True)
            if not res or not nxt or nxt == cursor or len(seen) >= a.max: break
            cursor = nxt; time.sleep(0.4)
    jf.close()
    rows = list(seen.values()); cols = list(rows[0].keys()) if rows else []
    with open(outcsv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(rows)
    if n_err > max(5, 0.005 * max(len(rows), 1)): raise SystemExit("trop de notices illisibles : %d" % n_err)
    print("OK : %d articles (%d nouveaux) -> %s" % (len(rows), n_new, outcsv))

if __name__ == "__main__": main()

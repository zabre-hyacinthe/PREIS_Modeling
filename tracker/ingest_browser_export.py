#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Convertit l'export CSV de la recherche Europe PMC faite par le navigateur (meme requete que config/search_protocol_v4.json)
en results/articles_v3_raw.csv (format de fetch_europepmc.py). Sert quand le reseau du poste ne permet pas le fetch direct.
Usage : python ingest_browser_export.py data/raw_v4/europepmc_v4_pubmed_2015_2026-11-26.csv"""
import csv, os, sys
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rules as R

def main():
    src = sys.argv[1]; root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    d = pd.read_csv(src, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    rows = []
    for r in d.itertuples(index=False):
        names = [x for x in (r.first_author, r.last_author) if x]; affs = [r.first_aff, r.last_aff][:len(names)]
        if len(names) == 2 and names[0] == names[1]: names, affs = names[:1], affs[:1]
        pt = [x.strip() for x in r.pubtypes.split(";") if x.strip()]
        o = dict(epmc_id=r.id, source=r.src, pmid=r.pmid, pmcid="", doi=r.doi, title=R.clean(r.title), abstract=R.clean(r.abstract), journal=r.journal,
                 first_pub_date=r.fpd, pub_year=r.year, cited_by=r.cited, is_open_access=r.oa, pub_types="|".join(pt), is_preprint=(r.src == "PPR"),
                 is_retracted=("Retracted Publication" in pt), grants="", keywords="", has_fulltext_oa=False,
                 url=("https://doi.org/" + r.doi) if r.doi else "https://europepmc.org/article/%s/%s" % (r.src, r.id), authors="; ".join(x for x in names if not x.startswith("(")))
        ai = R.author_info(names, affs)
        allc = {k for k, rx in R.COUNTRY_RE.items() if rx.search(r.all_aff or "")}     # tous les co-auteurs (export navigateur : texte d'affiliation agrege)
        ai["author_countries_africa"] = "|".join(sorted(allc | set(filter(None, ai["author_countries_africa"].split("|")))))
        ai["africa_any_author"] = bool(allc) or ai["africa_first_author"] or ai["africa_last_author"]
        ai["no_african_affiliation"] = (not ai["africa_any_author"]) and bool(r.first_aff or r.last_aff or r.all_aff)
        ai["n_authors"] = ""        # nombre total non fourni par l'export agrege
        o.update(ai); rows.append(o)
    out = os.path.join(root, "results", "articles_v3_raw.csv")
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    print("OK : %d articles -> %s" % (len(rows), out))

if __name__ == "__main__": main()

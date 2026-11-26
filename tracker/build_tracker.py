#!/usr/bin/env python3
"""PREIS Model Tracker v3 - reconstruit le tracker de modelisation a partir de V10 (lecture seule), avec regles explicites.
Entrees : PREIS_V10_March_4_26/dashboard/data/dashboard/articles.csv (+ prediction_tracker.csv pour comparer a la v1)
Sorties : results/model_tracker_v3.csv, results/quality_report.json, results/v1_vs_v2.csv ; ne modifie jamais V10.
Usage : python build_tracker.py [--v10 D:\\PREIS_V10_March_4_26]"""
import argparse, json, os, sys
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rules as R

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--v10", default=os.path.expanduser("~/mnt/d/PREIS_V10_March_4_26") if os.name != "nt" else r"D:\PREIS_V10_March_4_26")
    a = ap.parse_args()
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); out = os.path.join(root, "results"); os.makedirs(out, exist_ok=True)
    dd = os.path.join(a.v10, "dashboard", "data", "dashboard")
    raw3 = os.path.join(root, "results", "articles_v3_raw.csv")
    if os.path.exists(raw3):
        art = pd.read_csv(raw3, encoding="utf-8", low_memory=False, dtype=str, keep_default_na=False); art["pub_year"] = pd.to_numeric(art.pub_year, errors="coerce"); input_src = "Europe PMC v3 (auteurs, preprints)"
    else:
        art = pd.read_csv(os.path.join(dd, "articles.csv"), encoding="utf-8-sig", low_memory=False); input_src = "V10 articles.csv (sans auteurs : lancer fetch_europepmc.py)"
    v1p = os.path.join(dd, "prediction_tracker.csv")
    v1 = pd.read_csv(v1p, encoding="utf-8-sig", low_memory=False) if os.path.exists(v1p) else pd.DataFrame({"title": []})   # absent dans le nuage : comparaison v1 ignorée
    art["title_c"] = art.title.map(R.clean); art["key"] = art.title_c.map(R.norm_title)
    n0 = len(art); art = art[art.key != ""].drop_duplicates("key").copy(); n_dups = n0 - len(art)
    rows = []
    for r in art.itertuples(index=False):
        d = dict(title=r.title_c, abstract=R.clean(r.abstract), url=r.url if isinstance(r.url, str) else "", journal=getattr(r, "journal", ""), pub_year=r.pub_year)
        for c in ("doi", "pmid", "first_pub_date", "authors", "first_author", "last_author", "n_authors", "author_countries_africa", "africa_first_author", "africa_last_author", "africa_any_author", "africa_led", "no_african_affiliation", "is_preprint", "is_retracted", "cited_by", "is_open_access", "pub_types", "grants", "source", "epmc_id"):
            d[c] = getattr(r, c, "")
        d.update(R.geo(d["title"], d["abstract"])); d.update(R.model_class(d["title"], d["abstract"])); d.update(R.pathogen(d["title"], d["abstract"]))
        d.update(R.target_year(d["title"], d["abstract"], r.pub_year)); d.update(R.evidence(d["title"], d["abstract"])); d["key"] = r.key
        rows.append(d)
    T = pd.DataFrame(rows)
    for c in ("africa_first_author", "africa_last_author", "africa_any_author", "africa_led", "no_african_affiliation", "is_preprint", "is_retracted"):
        T[c] = T[c].map(lambda v: True if str(v) == "True" else (False if str(v) == "False" else None))
    T["in_v1_tracker"] = T.key.isin(set(v1.title.map(R.norm_title)))
    T["is_predictive_model"] = (T.model_class_v2 != "Non classé") & (T.modelling_confidence.isin(["élevée", "moyenne"])) & (~T.design_excluded | (T.modelling_confidence == "élevée"))
    # métadonnées Europe PMC (après le premier fetch) : les revues, éditoriaux, commentaires et lettres ne sont pas des études de modélisation
    nonres = T.pub_types.astype(str).str.contains(r"Review|Editorial|Comment|Letter|News|Retracted|Erratum|Guideline", case=False, regex=True)
    T["is_predictive_model"] = T.is_predictive_model & ~nonres
    T["in_scope"] = T.is_predictive_model & T.africa_relevance.isin(["Afrique", "Afrique (cadre à confirmer)", "Mondial (Afrique mentionnée)"]) & (T.domain_v2 == "Maladie infectieuse")
    T["core_africa_scope"] = T.in_scope & (T.africa_relevance == "Afrique")
    # file d'attente humaine : rien n'est perdu - modele detecte mais confiance faible / design douteux, infectieux, Afrique ou mondial
    T["review_status"] = "hors périmètre"
    cand = (T.model_class_v2 != "Non classé") & (T.domain_v2 == "Maladie infectieuse") & T.africa_relevance.isin(["Afrique", "Afrique (cadre à confirmer)", "Mondial (Afrique mentionnée)"]) & ~T.in_scope
    T.loc[cand, "review_status"] = "candidat à revoir (humain)"
    T.loc[T.in_scope, "review_status"] = "retenu (règles, non validé humain)"
    ev = [R.evidence_tier(t, a_, m) for t, a_, m in zip(T.title, T.abstract, T.is_predictive_model)]
    T = pd.concat([T, pd.DataFrame(ev)], axis=1)
    # suivi de realisation (protocole V9) : une prevision dont l'annee cible est passee doit etre confrontee aux observations
    cur = pd.Timestamp.today().year
    ty = pd.to_numeric(T.target_year_v2, errors="coerce")
    T["realization_status"] = "non applicable"
    T.loc[T.in_scope & ty.notna() & (ty > cur), "realization_status"] = "en attente (année cible future)"
    T.loc[T.in_scope & ty.notna() & (ty <= cur), "realization_status"] = "à vérifier (année cible atteinte)"
    T.drop(columns=["key"]).to_csv(os.path.join(out, "model_tracker_v3.csv"), index=False, encoding="utf-8")
    q = dict(
        universe_articles=n0, duplicates_removed=int(n_dups), v1_rows=len(v1),
        v2_predictive_models=int(T.is_predictive_model.sum()), v2_in_scope_infectious=int(T.in_scope.sum()), v2_core_africa_infectious=int(T.core_africa_scope.sum()),
        v1_in_v2_core=int((T.in_v1_tracker & T.core_africa_scope).sum()), v1_not_in_v2_scope=int((T.in_v1_tracker & ~T.in_scope).sum()),
        v2_core_not_in_v1=int((~T.in_v1_tracker & T.core_africa_scope).sum()),
        by_class=T[T.in_scope].model_class_v2.value_counts().to_dict(), by_pathogen=T[T.in_scope].pathogen_v2.value_counts().head(15).to_dict(),
        by_geo_scope=T[T.in_scope].geo_scope_v2.value_counts().to_dict(), by_year=T[T.in_scope].pub_year.value_counts().to_dict(),
        input_source=input_src, review_status=T.review_status.value_counts().to_dict(), by_evidence_tier=T[T.in_scope].evidence_tier.value_counts().sort_index().to_dict(), by_realization=T[T.in_scope].realization_status.value_counts().to_dict(),
        preprints_in_scope=int((T.in_scope & (T.is_preprint == True)).sum()), africa_led_share_core=(round(float((T[T.core_africa_scope].africa_led == True).sum()) / max(1, int(T[T.core_africa_scope].africa_led.notna().sum())), 2)),
        no_african_affiliation_core=int((T[T.core_africa_scope].no_african_affiliation == True).sum()),
        target_year_filled=int((T[T.in_scope].target_year_v2 != "").sum()), evidence_flags_dist=T[T.in_scope].evidence_flags.value_counts().sort_index().to_dict(),
        url_filled_pct=round(100 * (T[T.in_scope].url != "").mean(), 1))
    json.dump(q, open(os.path.join(out, "quality_report.json"), "w"), indent=1, ensure_ascii=False, default=str)
    print(json.dumps(q, indent=1, ensure_ascii=False, default=str))
if __name__ == "__main__": main()

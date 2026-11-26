#!/usr/bin/env python3
"""PREIS-Modeling : moteur d'alertes (publications de modelisation a signaler).
Entree : results/model_tracker_v3.csv + config/alert_rules.json. Sorties : data/alerting/alert_candidates.csv (meme role que PREIS AI) et hub_export/modeling_preis_signals.csv (contrat HUB).
Une alerte = une PUBLICATION de modelisation, pas un foyer epidemique. Chaque alerte porte ses raisons (signal_detail) : auditable."""
import json, os, sys, datetime as dt
import pandas as pd
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def run(today=None):
    today = today or dt.date.today(); cfg = json.load(open(os.path.join(root, "config", "alert_rules.json"), encoding="utf-8")); P = cfg["points"]
    T = pd.read_csv(os.path.join(root, "results", "model_tracker_v3.csv"), low_memory=False)
    A = T[(T.review_status == cfg["min_status"]) & T.africa_relevance.isin(["Afrique", "Afrique (cadre à confirmer)", "Mondial (Afrique mentionnée)"])].copy()
    pd_ = pd.to_datetime(A.get("first_pub_date"), errors="coerce") if "first_pub_date" in A else pd.Series(pd.NaT, index=A.index)
    age = (pd.Timestamp(today) - pd_).dt.days
    rows = []
    for (i, r), a in zip(A.iterrows(), age):
        s, why = 0, []
        def add(k, label):
            nonlocal s; s += P[k]; why.append("%s(%+d)" % (label, P[k]))
        if r.pathogen_v2 in cfg["priority_pathogens"]: add("priority_pathogen", "pathogène prioritaire")
        if r.pathogen_v2 in cfg["active_outbreak_pathogens"]: add("active_outbreak", "épidémie active/surveillée")
        if r.africa_relevance == "Afrique": add("core_africa", "centré Afrique")
        else: add("global_incl_africa", "mondial incl. Afrique")
        if str(r.model_class_v2) in ("Séries temporelles / prévision", "Projection de charge / tendances", "Simulation / scénarios", "Spatial / cartographie du risque", "Compartimental / mécaniste"): add("predictive_output", "sortie prédictive")
        if r.evidence_tier == "T4": add("tier_T4", "preuve T4")
        elif r.evidence_tier == "T3": add("tier_T3", "preuve T3")
        if pd.notna(a):
            if a <= 30: add("recent_30d", "≤30 j")
            elif a <= cfg["recent_window_days_default"]: add("recent_90d", "≤90 j")
        else:
            if int(r.pub_year) == today.year: add("recent_90d", "année en cours (date exacte indisponible)")
        if str(r.africa_led) == "True": add("africa_led", "dirigé depuis l'Afrique")
        if str(r.realization_status).startswith("à vérifier") or str(r.target_year_v2) not in ("", "nan") and float(r.target_year_v2 or 0) - today.year in (0, 1, 2): add("near_target_year", "horizon proche")
        if int(r.transparency_score) == 0: add("low_transparency_penalty", "aucun critère de transparence")
        lvl = "high" if s >= cfg["levels"]["high"] else ("medium" if s >= cfg["levels"]["medium"] else "low")
        rid = str(r.doi) if str(r.doi) not in ("", "nan") else str(r.url)
        rows.append(dict(record_id=rid, title=r.title, pub_year=r.pub_year, first_pub_date=r.get("first_pub_date", ""), doi=r.get("doi", ""), journal=r.get("journal", ""), url=r.url,
            countries=r.countries_name, pathogen=r.pathogen_v2, model_class=r.model_class_v2, method_terms=r.method_terms, evidence_tier=r.evidence_tier, transparency_score=r.transparency_score,
            is_preprint=r.get("is_preprint", ""), first_author=r.get("first_author", ""), africa_led=r.get("africa_led", ""), realization_status=r.realization_status,
            priority_score=s, priority_level=lvl, alert_tier=cfg["tiers"][lvl], signal_detail="; ".join(why), review_status=r.review_status, validation="non validé humain (règles + relecteurs IA)", generated_on=today.isoformat()))
    C = pd.DataFrame(rows).sort_values("priority_score", ascending=False)
    os.makedirs(os.path.join(root, "data", "alerting"), exist_ok=True); C.to_csv(os.path.join(root, "data", "alerting", "alert_candidates.csv"), index=False, encoding="utf-8")
    now = dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"); COLS = ["module","source","report_id","report_date","geo_level","geo_name","geo_code","indicator","value","value_type","signal_level","provisional","source_url","extracted_at"]
    sig = [["modeling", "PREIS-Modeling", r.record_id, today.isoformat(), "country" if ";" not in str(r.countries) and str(r.countries) not in ("", "nan") else "continent", r.countries if str(r.countries) not in ("", "nan") else "Afrique", "", "publication_modelisation:%s|%s|%s" % (r.pathogen, r.model_class, r.evidence_tier), r.priority_score, "score", r.priority_level, True, r.url, now] for r in C[C.priority_level.isin(["high", "medium"])].itertuples()]
    os.makedirs(os.path.join(root, "hub_export"), exist_ok=True); pd.DataFrame(sig, columns=COLS).to_csv(os.path.join(root, "hub_export", "modeling_preis_signals.csv"), index=False, encoding="utf-8")
    print("alertes candidates :", len(C), C.priority_level.value_counts().to_dict(), "| signaux HUB :", len(sig)); return C
if __name__ == "__main__": run()

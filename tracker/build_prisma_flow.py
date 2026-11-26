#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Flux PRISMA 2020 recalcule a chaque execution, avec motif code (I/E) de decision pour chaque enregistrement.
Entrees : results/model_tracker_v3.csv, config/search_protocol_v4.json. Sorties : data/derived/prisma_flow.csv ; results/screening_decisions.csv.
Ordre des motifs (cascade, un seul motif par enregistrement) : E2 retracte > E7 revue > E6 commentaire > E9 resume absent > E4 hors Afrique > E3 non infectieux > E5 pas de modele predictif."""
import json, os
import pandas as pd
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = pd.read_csv(os.path.join(root, "results", "model_tracker_v3.csv"), dtype=str, keep_default_na=False)
P = json.load(open(os.path.join(root, "config", "search_protocol_v4.json"), encoding="utf-8"))
raw = pd.read_csv(os.path.join(root, "results", "articles_v3_raw.csv"), dtype=str, keep_default_na=False, usecols=["epmc_id"])
n_ident = len(raw); n_dup = n_ident - len(T)
pt = T.pub_types.str.lower()
def code(r, p):
    if r.is_retracted == "True": return "E2"
    if "review" in p and "systematic" in p or p.startswith("review") or "|review" in p or "review-article" in p: return "E7"
    if any(k in p for k in ("editorial", "comment", "letter", "news")): return "E6"
    if len(r.abstract) < 50: return "E9"
    if r.africa_relevance == "Hors Afrique / non précisé": return "E4"
    if r.domain_v2.startswith("Hors périmètre"): return "E3"
    if r.in_scope == "True": return "INCLUS"
    if r.review_status.startswith("candidat"): return "A_REVOIR"
    if r.domain_v2 == "Non précisé": return "A_REVOIR"
    return "E5"
T["decision_code"] = [code(r, p) for r, p in zip(T.itertuples(index=False), pt)]
T[["epmc_id", "pmid", "doi", "title", "decision_code"]].to_csv(os.path.join(root, "results", "screening_decisions.csv"), index=False, encoding="utf-8")
c = T.decision_code.value_counts()
lab = {"E2": "E2 retractée", "E7": "E7 revue ou revue systématique (à part, tier T1)", "E6": "E6 commentaire, éditorial, lettre, actualité", "E9": "E9 résumé absent ou inexploitable",
       "E4": "E4 sans cadre africain", "E3": "E3 maladie non infectieuse", "E5": "E5 pas de modèle prédictif détecté"}
rows = [("Enregistrements identifiés (Europe PMC, PubMed, 2015 à aujourd'hui, sans préprints)", n_ident), ("Doublons retirés", n_dup), ("Enregistrements examinés", len(T))]
rows += [(lab[k], int(c.get(k, 0))) for k in lab]
rows += [("Domaine ou modèle à confirmer par un humain (file de revue)", int(c.get("A_REVOIR", 0))), ("Études incluses (règles, non validé humain)", int(c.get("INCLUS", 0)))]
F = pd.DataFrame(rows, columns=["etape", "n"]); os.makedirs(os.path.join(root, "data", "derived"), exist_ok=True)
F.to_csv(os.path.join(root, "data", "derived", "prisma_flow.csv"), index=False, encoding="utf-8")
assert F.n.iloc[3:].sum() == len(T), "la cascade doit couvrir tous les enregistrements"
print(F.to_string(index=False))

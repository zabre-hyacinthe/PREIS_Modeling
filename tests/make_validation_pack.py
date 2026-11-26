"""Construit le paquet de validation (200 articles, stratifie, AVEUGLE) pour la triangulation. Usage : python make_validation_pack.py [--seed 4242]"""
import argparse, os, pandas as pd
ap = argparse.ArgumentParser(); ap.add_argument("--seed", type=int, default=4242); a = ap.parse_args()
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = pd.read_csv(os.path.join(root, "results", "model_tracker_v3.csv")); T["rid"] = T.index
strata = {
 "A_core_africa": T[T.core_africa_scope], "B_in_scope_autre": T[T.in_scope & ~T.core_africa_scope],
 "C_quasi_exclus": T[(~T.in_scope) & (T.model_class_v2 != "Non classé") & (T.domain_v2 == "Maladie infectieuse")],
 "D_hasard": T[(~T.in_scope) & (T.model_class_v2 == "Non classé")]}
n = {"A_core_africa": 70, "B_in_scope_autre": 25, "C_quasi_exclus": 65, "D_hasard": 40}
S = pd.concat([strata[k].sample(min(n[k], len(strata[k])), random_state=a.seed).assign(stratum=k, pop=len(strata[k])) for k in n])
S = S.sample(frac=1, random_state=a.seed).reset_index(drop=True); S["sid"] = ["V%03d" % (i + 1) for i in range(len(S))]
os.makedirs(os.path.join(root, "pack"), exist_ok=True)
S[["sid", "title", "abstract", "url", "pub_year"]].to_csv(os.path.join(root, "pack", "validation_pack_blind.csv"), index=False, encoding="utf-8-sig")
S[["sid", "rid", "stratum", "pop", "in_scope", "core_africa_scope", "is_predictive_model", "model_class_v2", "pathogen_v2", "africa_relevance", "domain_v2", "evidence_tier"]].to_csv(os.path.join(root, "pack", "_KEY_hidden_do_not_share.csv"), index=False)
print(len(S), S.stratum.value_counts().to_dict())

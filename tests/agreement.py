"""Accord inter-relecteurs (kappa de Fleiss) + comparaison tracker vs consensus, pondérée par strate.
Usage : python agreement.py [dossier_labels]  (fichiers reviewer_*.csv ; humains : reviewer_H1.csv ...)"""
import glob, os, sys, json, numpy as np, pandas as pd
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
d = sys.argv[1] if len(sys.argv) > 1 else os.path.join(root, "pack", "labels")
L = {os.path.basename(f)[9:-4]: pd.read_csv(f, dtype=str).set_index("sid") for f in sorted(glob.glob(os.path.join(d, "reviewer_*.csv")))}
K = pd.read_csv(os.path.join(root, "pack", "_KEY_hidden_do_not_share.csv")).set_index("sid")
sids = sorted(set.intersection(*[set(v.index) for v in L.values()])); names = list(L)
def fleiss(col):
    cats = sorted({x for v in L.values() for x in v.loc[sids, col].dropna()}); idx = {c: i for i, c in enumerate(cats)}
    M = np.zeros((len(sids), len(cats)))
    for v in L.values():
        for i, s in enumerate(sids):
            x = v.loc[s, col]
            if isinstance(x, str) and x in idx: M[i, idx[x]] += 1
    n = M.sum(1); ok = n >= 2; M = M[ok]; n = n[ok]
    Pi = ((M * (M - 1)).sum(1)) / (n * (n - 1)); Pbar = Pi.mean(); pj = M.sum(0) / M.sum()
    Pe = (pj ** 2).sum(); return round(float((Pbar - Pe) / (1 - Pe)) if Pe < 1 else float("nan"), 2), round(float(Pbar), 2)
out = {"n_reviewers": len(L), "reviewers": names, "n_articles": len(sids)}
for c in ["is_model", "infectious", "africa_setting", "model_class", "predictive_output", "evidence_tier"]:
    out["kappa_" + c], out["agree_" + c] = fleiss(c)
def maj(col):
    r = {}
    for s in sids:
        v = [L[n].loc[s, col] for n in names if isinstance(L[n].loc[s, col], str)]
        vc = pd.Series(v).value_counts(); r[s] = vc.index[0] if len(vc) and (len(vc) == 1 or vc.iloc[0] > vc.iloc[1]) else "NO_MAJORITY"
    return pd.Series(r)
C = pd.DataFrame({c: maj(c) for c in ["is_model", "infectious", "africa_setting", "model_class", "predictive_output", "evidence_tier"]})
C["truth_in_scope"] = (C.is_model == "Y") & (C.infectious == "Y") & C.africa_setting.isin(["africa_specific", "multi_incl_africa", "global_incl_africa"])
C["truth_core"] = (C.is_model == "Y") & (C.infectious == "Y") & (C.africa_setting == "africa_specific")
C["disagreement"] = (C == "NO_MAJORITY").any(axis=1) | (C[["is_model", "infectious", "africa_setting"]].apply(lambda r: any(len({L[n].loc[r.name, c] for n in names}) > 1 for c in r.index), axis=1))
J = C.join(K, lsuffix="_cons", rsuffix="_trk"); J.to_csv(os.path.join(root, "pack", "consensus_and_tracker.csv"))
def w_metrics(pred, truth, label):
    # estimateurs ponderes par strate : N_h = taille de la population de la strate, n_h = echantillon
    tp = fp = fn = 0.0
    for h, g in J.groupby("stratum"):
        w = g["pop"].iloc[0] / len(g); tp += w * (g[pred] & g[truth]).sum(); fp += w * (g[pred] & ~g[truth]).sum(); fn += w * (~g[pred] & g[truth]).sum()
    p = tp / (tp + fp) if tp + fp else float("nan"); r = tp / (tp + fn) if tp + fn else float("nan")
    return {"precision_w": round(p, 2), "recall_w": round(r, 2), "TP_est": round(tp), "FP_est": round(fp), "FN_est": round(fn)}
J["in_scope"] = J.in_scope.astype(bool); J["core_africa_scope"] = J.core_africa_scope.astype(bool)
out["tracker_vs_consensus_in_scope"] = w_metrics("in_scope", "truth_in_scope", "in"); out["tracker_vs_consensus_core"] = w_metrics("core_africa_scope", "truth_core", "core")
out["articles_en_desaccord_a_adjuger_par_humains"] = int(J.disagreement.sum())
tier = J[J.truth_in_scope]; out["tier_tracker_vs_consensus_exact"] = round(float((tier.evidence_tier_cons == tier.evidence_tier_trk).mean()), 2) if "evidence_tier_cons" in tier else None
json.dump(out, open(os.path.join(root, "pack", "agreement_report.json"), "w"), indent=1, ensure_ascii=False); print(json.dumps(out, indent=1, ensure_ascii=False))

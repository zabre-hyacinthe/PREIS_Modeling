import os, sys, pandas as pd
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tracker"))
import send_alerts as S
# donnees SYNTHETIQUES de test (aucune vraie publication)
N = pd.DataFrame([
 dict(record_id="a", pathogen="Mpox", countries="Nigeria", priority_level="high", priority_score=12, alert_tier="immediate"),
 dict(record_id="b", pathogen="Choléra", countries="Kenya; Uganda", priority_level="medium", priority_score=7, alert_tier="weekly"),
 dict(record_id="c", pathogen="Paludisme", countries="", priority_level="medium", priority_score=6, alert_tier="weekly"),
 dict(record_id="d", pathogen="Mpox", countries="Ghana", priority_level="low", priority_score=2, alert_tier="monthly"),
])
run = ["immediate", "weekly"]
cdc = S.profile(dict(email="x", audience="africa_cdc"))
assert set(S.route(N, cdc, run).record_id) == {"a", "b", "c"}                   # niveau mini medium, paliers du jour
assert set(S.route(N, cdc, ["immediate"]).record_id) == {"a"}                   # weekly non declenche aujourd'hui
moh = S.profile(dict(email="x", audience="moh", countries="Nigeria", pathogens="Mpox", include_continental="no"))
assert list(S.route(N, moh, run).record_id) == ["a"]                            # pays + maladie
rcc = S.profile(dict(email="x", audience="rcc", countries="Kenya;Ethiopia"))
assert set(S.route(N, rcc, run).record_id) == {"b", "c"}                        # Kenya touche ; continental inclus
partner = S.profile(dict(email="x", audience="partner"))
assert S.route(N, partner, ["immediate"]).empty                                 # partenaire = weekly/monthly seulement
for c,v in dict(url="https://x.invalid",title="T",model_class="Compartimental",evidence_tier="T3",signal_detail="d").items(): N[c]=v
assert len(S.rcpt_hash("A@b.org")) == 10 and S.rcpt_hash("A@b.org") == S.rcpt_hash(" a@b.org ")
subj, body, text = S.build_message(S.route(N, cdc, run), cdc, "2026-11-26", "contact@exemple.invalid")
assert "high priority" in subj and "not yet validated by humans" in body and "Mpox" in text
print("routing tests ok")

# anglais par defaut (27/11/2026)
assert "Read before acting" in body and "Priorité" not in body and "Pourquoi" not in body, "email non anglais"
print("english email OK")

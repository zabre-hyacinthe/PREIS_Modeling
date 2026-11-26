import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tracker"))
from backtest import score_record, wis_interval
B = dict(prediction_date="2020-01-01", target_start="2020-02-01", target_end="2020-03-01", kind="interval", observed_source="TEST")
# synthetic: tests only, not real predictions
assert score_record({**B, "point":100,"lo":80,"hi":120,"observed":90})["verdict"]=="confirmee"
assert score_record({**B, "kind":"point","point":100,"observed":300})["verdict"]=="infirmee"
assert score_record({**B, "kind":"point","point":100,"observed":160})["verdict"]=="partiellement confirmee"
assert score_record({**B, "kind":"point","point":100})["status"]=="en attente"
assert score_record({**B, "kind":"point","point":100,"observed":100,"observed_source":""})["status"]=="non evaluable"
assert score_record({**B, "prediction_date":"2020-04-01","kind":"point","point":1,"observed":1})["status"]=="invalide"
assert score_record({**B, "kind":"point","point":100,"observed":100,"scenario_conditional":"Y"})["status"]=="en attente"
assert score_record({**B, "kind":"point","point":100,"observed":100,"scenario_conditional":"Y","assumptions_held":"N"})["status"]=="non evaluable"
s = score_record({**B, "kind":"point","point":100,"observed":120,"null_forecast":50}); assert abs(s["skill_vs_null"]-(1-20/70))<1e-9
assert score_record({**B,"kind":"binary","prob":0.8,"observed":1})["brier"]<0.05
assert abs(wis_interval(80,120,130,0.95)-(40+40*10))<1e-9
print("backtest tests ok")
